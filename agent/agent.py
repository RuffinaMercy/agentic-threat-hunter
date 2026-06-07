import argparse
import base64
import hmac
import hashlib
import json
import os
import re
import time
import concurrent.futures
import tempfile
import subprocess
import shutil
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional

import arxiv
import feedparser
import requests
import yaml
from dotenv import load_dotenv
from groq import Groq

from logger import log_event, record_step, record_error, record_llm_tokens, record_code_execution, log_exception, finalize_run

load_dotenv()

# Paths relative to project root (one level up from agent/)
PROJECT_ROOT = Path(__file__).resolve().parent.parent
STATE_FILE = PROJECT_ROOT / "data" / "agent_state.json"
SKILLS_DIR = PROJECT_ROOT / "skills"
POLICIES_FILE = Path(__file__).resolve().parent / "policies.yaml"
TASK_DESCRIPTION = "Summarize today's top AI news in 3 bullet points, neutral tone, include sources"

REDDIT_URL = "https://www.reddit.com/r/MachineLearning/top.json"
GOOGLE_NEWS_RSS_URL = (
    "https://news.google.com/rss/search"
    "?q=artificial+intelligence&hl=en-US&gl=US&ceid=US:en"
)
HACKER_NEWS_TOP_URL = "https://hacker-news.firebaseio.com/v0/topstories.json"
HACKER_NEWS_ITEM_URL = "https://hacker-news.firebaseio.com/v0/item/{}.json"

GROQ_SKILL_SELECTOR_MODEL = os.getenv("GROQ_SKILL_SELECTOR_MODEL", "llama-3.1-8b-instant")
GROQ_SUMMARIZER_MODEL = os.getenv("GROQ_SUMMARIZER_MODEL", "llama-3.3-70b-versatile")
# SKILL_SIGNING_KEY is now retrieved via signing_key_bytes() with fallbacks

POLICIES: Dict[str, Any] = {}
_item_summaries: Dict[str, str] = {}   # store per‑item short summaries from last LLM call

# ------------------------------------------------------------------
# Cisco Skill Scanner integration (pre‑execution security check)
# ------------------------------------------------------------------
def scan_skill_with_cisco(skill: Dict[str, Any]) -> tuple[bool, str]:
    """
    Converts a skill JSON to a temporary skill directory, runs Cisco Skill Scanner,
    and returns (is_safe, message).
    Rejects if any CRITICAL or HIGH severity findings are found (count > 0).
    """
    if shutil.which("skill-scanner") is None:
        log("Warning: skill-scanner not found in PATH. Skipping pre‑execution scan.")
        return True, "scanner not available"

    temp_dir = tempfile.mkdtemp(prefix="skill_scan_")
    try:
        skill_name = skill.get("name", "unnamed")
        description = skill.get("description", "")
        yaml_frontmatter = f"""---
name: {skill_name}
description: {description}
---
"""
        if "instructions" in skill:
            instr = skill["instructions"]
            if isinstance(instr, str) and len(instr) % 4 == 0:
                try:
                    decoded = base64.b64decode(instr).decode('utf-8')
                    instr = decoded
                except Exception:
                    pass
            body = instr
        elif "code" in skill:
            body = f"# Code skill\n\nThis skill executes the following Python code:\n```python\n{skill['code']}\n```"
        else:
            body = "No instructions or code provided."

        skill_md_path = Path(temp_dir) / "SKILL.md"
        skill_md_path.write_text(yaml_frontmatter + body, encoding="utf-8")

        if "code" in skill:
            script_path = Path(temp_dir) / "script.py"
            script_path.write_text(skill["code"], encoding="utf-8")

        cmd = ["skill-scanner", "scan", str(temp_dir)]
        if os.getenv("SKILL_SCANNER_LLM_API_KEY"):
            cmd.append("--use-behavioral")

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        output = result.stdout + result.stderr

        # Parse severity counts
        critical_match = re.search(r'CRITICAL:\s*(\d+)', output)
        high_match = re.search(r'HIGH:\s*(\d+)', output)
        critical_count = int(critical_match.group(1)) if critical_match else 0
        high_count = int(high_match.group(1)) if high_match else 0

        if critical_count > 0 or high_count > 0:
            lines = [line.strip() for line in output.split('\n') if "CRITICAL" in line or "HIGH" in line]
            summary = f"Scanner blocked skill: {', '.join(lines[:3])}"
            return False, summary
        else:
            return True, "Scanner passed"
    except subprocess.TimeoutExpired:
        log("Scanner timed out – allowing skill (fail open).")
        return True, "scanner timeout"
    except Exception as e:
        log(f"Scanner error: {e} – allowing skill (fail open).")
        return True, f"scanner error: {e}"
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)

# ------------------------------------------------------------------
# Existing helper functions
# ------------------------------------------------------------------
def load_policies(policy_file: Path) -> Dict[str, Any]:
    if not policy_file.exists():
        log("Warning: policies.yaml not found. Using permissive defaults.")
        return {
            "default_behavior": "ask",
            "max_steps": 10,
            "skills": {},
            "sandbox": {"timeout": 15, "memory_limit": "128m"}
        }
    try:
        with open(policy_file, "r", encoding="utf-8") as f:
            policies = yaml.safe_load(f) or {}
    except Exception as e:
        log(f"Error loading policies.yaml: {e}. Using defaults.")
        return {
            "default_behavior": "ask",
            "max_steps": 10,
            "skills": {},
            "sandbox": {"timeout": 15, "memory_limit": "128m"}
        }
    policies.setdefault("default_behavior", "ask")
    policies.setdefault("max_steps", 10)
    policies.setdefault("skills", {})
    policies.setdefault("sandbox", {"timeout": 15, "memory_limit": "128m"})
    log_event(
        "policy_load",
        policy_file=str(policy_file),
        default_behavior=policies["default_behavior"],
        num_skills=len(policies.get("skills", {})),
        max_steps=policies["max_steps"]
    )
    return policies

def policy_allows_skill(skill_name: str, policies: Dict[str, Any]) -> tuple[bool, str]:
    skills_config = policies.get("skills", {})
    for skill_rule in skills_config:
        if skill_rule.get("name") == skill_name:
            if not skill_rule.get("allowed", False):
                return False, "policy_denied"
            if skill_rule.get("require_approval", False):
                return True, "ask_user"
            return True, "policy_allowed"
    default = policies.get("default_behavior", "ask").lower()
    if default == "allow":
        return True, "policy_allowed"
    elif default == "deny":
        return False, "policy_denied"
    else:
        return True, "ask_user"

def log(message: str) -> None:
    print(f"[agent] {message}", flush=True)

def today_iso() -> str:
    return date.today().isoformat()

def maybe_decode_instructions(instructions: str) -> str:
    if len(instructions) % 4 == 0 and all(c in "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=" for c in instructions):
        try:
            decoded = base64.b64decode(instructions).decode('utf-8')
            print(f"[agent] Decoded base64 instructions: {decoded[:200]}...")
            return decoded
        except:
            pass
    return instructions

def fresh_state() -> Dict[str, Any]:
    return {
        "date": today_iso(),
        "step": 0,
        "raw_news": [],
        "chosen_skill_name": None,
        "final_summary": None,
        "item_summaries": {},
        "done": False,
    }

def load_state() -> Dict[str, Any]:
    if not STATE_FILE.exists():
        return fresh_state()
    try:
        state = json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        log("State file is invalid JSON. Starting fresh.")
        return fresh_state()
    required = {"date", "step", "raw_news", "chosen_skill_name", "final_summary", "done"}
    if not required.issubset(state):
        log("State file is missing required fields. Starting fresh.")
        return fresh_state()
    if state["date"] != today_iso():
        log(f"State is from {state['date']}; starting fresh for {today_iso()}.")
        return fresh_state()
    if "item_summaries" not in state:
        state["item_summaries"] = {}
    return state

def save_state(state: Dict[str, Any]) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")

def fetch_reddit(limit: int = 5) -> List[Dict[str, str]]:
    log("Fetching Reddit r/MachineLearning top daily posts.")
    response = requests.get(
        REDDIT_URL,
        params={"t": "day", "limit": limit},
        headers={"User-Agent": "daily-ai-news-agent/1.0"},
        timeout=15,
    )
    response.raise_for_status()
    items = []
    data = response.json()
    for child in data.get("data", {}).get("children", [])[:limit]:
        post = child.get("data", {})
        title = post.get("title")
        if not title:
            continue
        permalink = post.get("permalink", "")
        items.append({
            "source": "Reddit",
            "title": title,
            "url": f"https://www.reddit.com{permalink}" if permalink else "",
            "summary": (post.get("selftext") or "")[:700],
        })
    return items

def fetch_google_news(limit: int = 5) -> List[Dict[str, str]]:
    log('Fetching Google News RSS for "artificial intelligence".')
    feed = feedparser.parse(GOOGLE_NEWS_RSS_URL)
    items = []
    for entry in feed.entries[:limit]:
        title = entry.get("title", "")
        if not title:
            continue
        items.append({
            "source": "Google News",
            "title": title,
            "url": entry.get("link", ""),
            "summary": entry.get("summary", ""),
        })
    return items

def fetch_arxiv_with_timeout(limit: int = 5, timeout: int = 10) -> List[Dict[str, str]]:
    def _fetch():
        client = arxiv.Client(page_size=limit, delay_seconds=1, num_retries=1)
        search = arxiv.Search(
            query="cat:cs.AI",
            max_results=limit,
            sort_by=arxiv.SortCriterion.SubmittedDate,
            sort_order=arxiv.SortOrder.Descending,
        )
        items = []
        for result in client.results(search):
            items.append({
                "source": "arXiv",
                "title": result.title,
                "url": result.entry_id,
                "summary": result.summary,
            })
        return items
    with concurrent.futures.ThreadPoolExecutor() as executor:
        future = executor.submit(_fetch)
        try:
            return future.result(timeout=timeout)
        except concurrent.futures.TimeoutError:
            log("arXiv fetch timed out – skipping.")
            return []

def fetch_hackernews(limit: int = 5) -> List[Dict[str, str]]:
    log("Fetching Hacker News top stories.")
    try:
        resp = requests.get(HACKER_NEWS_TOP_URL, timeout=10)
        resp.raise_for_status()
        top_ids = resp.json()[:limit]
    except Exception as e:
        log(f"Hacker News top stories failed: {e}")
        return []
    items = []
    for story_id in top_ids:
        try:
            url = HACKER_NEWS_ITEM_URL.format(story_id)
            story_resp = requests.get(url, timeout=10)
            story_resp.raise_for_status()
            story = story_resp.json()
            title = story.get("title", "")
            if not title:
                continue
            items.append({
                "source": "Hacker News",
                "title": title,
                "url": story.get("url", f"https://news.ycombinator.com/item?id={story_id}"),
                "summary": "",
            })
        except Exception as e:
            log(f"Failed to fetch Hacker News item {story_id}: {e}")
            continue
    return items

def fetch_news() -> List[Dict[str, str]]:
    start_time = time.time()
    raw_news: List[Dict[str, str]] = []
    sources_fetched = []
    try:
        items = fetch_reddit()
        if items:
            sources_fetched.append("Reddit")
            raw_news.extend(items)
    except Exception as exc:
        log(f"Warning: Reddit failed: {exc}")
        log_exception(exc, context={"fetcher": "Reddit"})
    try:
        items = fetch_google_news()
        if items:
            sources_fetched.append("GoogleNews")
            raw_news.extend(items)
    except Exception as exc:
        log(f"Warning: Google News failed: {exc}")
        log_exception(exc, context={"fetcher": "GoogleNews"})
    try:
        items = fetch_arxiv_with_timeout(limit=3, timeout=10)
        if items:
            sources_fetched.append("Arxiv")
            raw_news.extend(items)
    except Exception as exc:
        log(f"Warning: arXiv failed: {exc}")
        log_exception(exc, context={"fetcher": "Arxiv"})
    try:
        items = fetch_hackernews(limit=3)
        if items:
            sources_fetched.append("HackerNews")
            raw_news.extend(items)
    except Exception as exc:
        log(f"Warning: Hacker News failed: {exc}")
        log_exception(exc, context={"fetcher": "HackerNews"})
    duration = time.time() - start_time
    log(f"Fetched {len(raw_news)} total news items from {len(sources_fetched)} source(s).")
    log_event("news_fetch", sources=sources_fetched, count=len(raw_news), duration_seconds=duration)
    return raw_news

def canonical_skill_json(skill: Dict[str, Any]) -> str:
    return json.dumps(skill, sort_keys=True, separators=(',', ':'), ensure_ascii=False)

# ------------------------------------------------------------
# Multi‑source signing key retrieval (works on Windows + Cloud)
# ------------------------------------------------------------
def signing_key_bytes() -> bytes:
    """
    Retrieve HMAC signing key from multiple sources:
    1. Streamlit secrets (for cloud deployment)
    2. Windows Credential Manager (local development)
    3. Environment variable (fallback)
    """
    # 1. Try Streamlit secrets (cloud)
    try:
        import streamlit as st
        hex_key = st.secrets.get("SKILL_SIGNING_KEY")
        if hex_key:
            log("[key] Using SKILL_SIGNING_KEY from Streamlit secrets.")
            return bytes.fromhex(hex_key)
    except (ImportError, FileNotFoundError, AttributeError, KeyError):
        pass  # Not in Streamlit or secret not set

    # 2. Try Windows Credential Manager (local)
    try:
        import keyring
        hex_key = keyring.get_password("skill_marketplace", "SKILL_SIGNING_KEY")
        if hex_key:
            log("[key] Using SKILL_SIGNING_KEY from Windows Credential Manager.")
            return bytes.fromhex(hex_key)
    except (ImportError, RuntimeError):
        pass  # keyring not available or not on Windows

    # 3. Fallback to environment variable (for testing)
    hex_key = os.getenv("SKILL_SIGNING_KEY")
    if hex_key:
        log("[key] Using SKILL_SIGNING_KEY from environment variable (fallback).")
        return bytes.fromhex(hex_key)

    # If nothing works, raise clear error
    raise RuntimeError(
        "SKILL_SIGNING_KEY not found. "
        "For Streamlit Cloud: add it to Secrets. "
        "For local Windows: run agent/store_key.py. "
        "For testing: set SKILL_SIGNING_KEY env var."
    )

def verify_skill(skill: Dict[str, Any]) -> bool:
    provided_signature = skill.get("signature")
    if not isinstance(provided_signature, str) or not provided_signature:
        return False
    unsigned_skill = dict(skill)
    unsigned_skill.pop("signature", None)
    unsigned_skill.pop("_path", None)
    digest = hmac.new(signing_key_bytes(), canonical_skill_json(unsigned_skill).encode("utf-8"), hashlib.sha256).hexdigest()
    return hmac.compare_digest(digest, provided_signature)

def load_skills(skip_verification: bool = False) -> List[Dict[str, Any]]:
    if not SKILLS_DIR.exists():
        SKILLS_DIR.mkdir(parents=True, exist_ok=True)
        log("Created missing skills/ folder. Add at least one skill JSON file and run again.")
        raise SystemExit(0)
    skills = []
    for path in sorted(SKILLS_DIR.glob("*.json")):
        try:
            skill = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            log(f"Skipping invalid skill {path.name}: {exc}")
            continue
        missing = {"name", "description"} - set(skill)
        if missing:
            log(f"Skipping {path.name}; missing fields: {', '.join(sorted(missing))}")
            continue
        if "instructions" not in skill and "code" not in skill:
            log(f"Skipping {path.name}; missing instructions or code")
            continue

        # Pre‑execution scanning (only if not skipping verification)
        if not skip_verification:
            is_safe, msg = scan_skill_with_cisco(skill)
            if not is_safe:
                log(f"Skill {path.name} BLOCKED by security scanner: {msg}")
                continue

        # HMAC verification
        if not skip_verification and not verify_skill(skill):
            log(f"Integrity check failed – skill rejected: {path.name}")
            continue

        skill["_path"] = str(path)
        skills.append(skill)

    if not skills:
        log("No valid signed skills found. Sign skills or use --skip-verification.")
        raise SystemExit(0)
    log(f"Loaded {len(skills)} skill(s).")
    return skills

def get_groq_client() -> Groq:
    # For Streamlit Cloud, try secrets first; fallback to env
    groq_key = None
    try:
        import streamlit as st
        groq_key = st.secrets.get("GROQ_API_KEY")
    except (ImportError, FileNotFoundError, AttributeError, KeyError):
        pass
    if not groq_key:
        groq_key = os.getenv("GROQ_API_KEY")
    if not groq_key:
        raise RuntimeError("GROQ_API_KEY missing. Set it in Streamlit secrets or environment.")
    return Groq(api_key=groq_key)

def choose_skill(client, skills):
    best = max(skills, key=lambda s: (s.get("rating", 0), s.get("downloads", 0)))
    log(f"Selected highest rated skill: {best['name']} (rating {best.get('rating', 0)})")
    log_event("skill_selection", chosen_skill=best["name"], alternatives=[s["name"] for s in skills],
              selection_method="highest_rating", rating=best.get("rating", 0), downloads=best.get("downloads", 0))
    return best["name"]

def find_skill(skills: List[Dict[str, Any]], skill_name: Optional[str]) -> Dict[str, Any]:
    for skill in skills:
        if skill["name"] == skill_name:
            return skill
    raise RuntimeError(f"Chosen skill {skill_name!r} not found.")

def permission_gate(skill, policies: Dict[str, Any]):
    allowed, reason = policy_allows_skill(skill["name"], policies)
    if reason == "policy_denied":
        log(f"Skill {skill['name']} denied by policy")
        log_event("permission_gate", skill_name=skill["name"], approved=False, reason="policy_denied")
        return False
    if reason == "policy_allowed":
        log(f"Skill {skill['name']} allowed by policy (no approval)")
        log_event("permission_gate", skill_name=skill["name"], approved=True, reason="policy_approved")
        return True
    print("\n=== Skill Permission Gate ===")
    print(f"Skill name: {skill['name']}")
    if "instructions" in skill:
        decoded = maybe_decode_instructions(skill["instructions"])
        print("\nInstructions:\n", decoded)
    elif "code" in skill:
        print("\nCode (preview):\n", skill["code"][:500] + ("..." if len(skill["code"]) > 500 else ""))
    else:
        print("\n(No instructions or code)")
    print("=============================\n")
    approval = os.getenv("AGENT_APPROVE_SKILL", "").strip().lower()
    if approval:
        allowed = approval in {"1", "true", "yes", "y", "approve", "approved"}
        log(f"Skill approval from env: {'approved' if allowed else 'denied'}.")
        log_event("permission_gate", skill_name=skill["name"], approved=allowed, reason="user_approved" if allowed else "user_denied")
        return allowed
    answer = input("Execute this skill? (yes/no): ").strip().lower()
    user_approved = answer == "yes"
    log(f"User approval: {'approved' if user_approved else 'denied'}.")
    log_event("permission_gate", skill_name=skill["name"], approved=user_approved, reason="user_approved" if user_approved else "user_denied")
    return user_approved

def run_code_skill_in_sandbox(code: str) -> str:
    import subprocess
    try:
        result = subprocess.run(["python", str(Path(__file__).resolve().parent / "sandbox_docker.py"), code], capture_output=True, text=True, timeout=15)
        stdout = result.stdout.strip()
        stderr = result.stderr.strip()
        if result.returncode != 0:
            parts = [f"ERROR (exit {result.returncode}):"]
            if stdout: parts.append(stdout)
            if stderr: parts.append(stderr)
            return "\n".join(parts)
        if stderr:
            return "\n".join(part for part in [stdout, stderr] if part)
        return stdout or "[Sandbox] No output"
    except subprocess.TimeoutExpired:
        return "[Sandbox] Code execution timed out"

def execute_skill(client: Groq, skill: Dict[str, Any], raw_news: List[Dict[str, str]]) -> str:
    global _item_summaries
    if "code" in skill:
        log("Executing code skill in Docker sandbox...")
        start_time = time.time()
        output = run_code_skill_in_sandbox(skill["code"])
        duration = time.time() - start_time
        success = not output.startswith("ERROR")
        record_code_execution()
        log_event("code_execution", skill_name=skill["name"], code_preview=skill["code"][:200],
                  success=success, output=output[:500], duration_seconds=duration)
        return f"[Sandbox output]\n{output}"
    if "instructions" in skill:
        skill["instructions"] = maybe_decode_instructions(skill["instructions"])
    log(f"Executing text skill: {skill['name']}")
    start_time = time.time()
    response = client.chat.completions.create(
        model=GROQ_SUMMARIZER_MODEL,
        temperature=0.2,
        max_tokens=2000,
        messages=[
            {"role": "system", "content": skill["instructions"]},
            {"role": "user", "content": f"News items:\n{json.dumps(raw_news, indent=2)}"},
        ],
    )
    duration = time.time() - start_time
    usage = response.usage
    record_llm_tokens(prompt_tokens=getattr(usage, 'prompt_tokens', 0),
                      completion_tokens=getattr(usage, 'completion_tokens', 0))
    log_event("llm_call", model=GROQ_SUMMARIZER_MODEL,
              prompt_tokens=getattr(usage, 'prompt_tokens', 0),
              completion_tokens=getattr(usage, 'completion_tokens', 0),
              duration_seconds=duration)
    raw_output = response.choices[0].message.content.strip()
    # Try to parse JSON
    try:
        json_str = re.sub(r'^```json\s*|\s*```$', '', raw_output, flags=re.MULTILINE).strip()
        data = json.loads(json_str)
        overall = data.get("overall_summary", "")
        items = data.get("items", [])
        _item_summaries = {}
        for it in items:
            if "title" in it and "short_summary" in it:
                _item_summaries[it["title"]] = it["short_summary"]
        return overall
    except (json.JSONDecodeError, KeyError, TypeError) as e:
        log(f"Failed to parse JSON response: {e}. Falling back to raw output.")
        return raw_output

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-verification", action="store_true")
    parser.add_argument("--policy", type=Path, default=POLICIES_FILE)
    return parser.parse_args()

def main() -> int:
    global _item_summaries
    try:
        args = parse_args()
        global POLICIES
        POLICIES = load_policies(args.policy)
        state = load_state()
        if state.get("done") and state.get("date") == today_iso():
            log("Today's briefing already complete. Printing stored summary.")
            print("\n" + (state.get("final_summary") or ""), flush=True)
            return 0
        if state["step"] <= 0:
            log("Step 0/3: Fetch news.")
            log_event("step_start", step=0, name="fetch_news")
            start_time = time.time()
            state["raw_news"] = fetch_news()
            state["step"] = 1
            save_state(state)
            record_step()
            log_event("step_end", step=0, name="fetch_news", duration_seconds=time.time() - start_time)
            log("Step 0 complete. State saved.")
        skills = load_skills(skip_verification=args.skip_verification)
        client = get_groq_client()
        if state["step"] <= 1:
            log("Step 1/3: Choose marketplace skill.")
            log_event("step_start", step=1, name="choose_skill")
            start_time = time.time()
            state["chosen_skill_name"] = choose_skill(client, skills)
            state["step"] = 2
            save_state(state)
            record_step()
            log_event("step_end", step=1, name="choose_skill", duration_seconds=time.time() - start_time)
            log("Step 1 complete. State saved.")
        if state["step"] <= 2:
            log("Step 2/3: Permission gate and skill execution.")
            log_event("step_start", step=2, name="permission_and_execute")
            start_time = time.time()
            chosen_skill = find_skill(skills, state["chosen_skill_name"])
            if not permission_gate(chosen_skill, POLICIES):
                log("Skill execution denied. Exiting.")
                record_step()
                save_state(state)
                log_event("step_end", step=2, name="permission_and_execute", duration_seconds=time.time() - start_time)
                return 2
            state["final_summary"] = execute_skill(client, chosen_skill, state["raw_news"])
            if _item_summaries:
                state["item_summaries"] = _item_summaries
            state["done"] = True
            save_state(state)
            record_step()
            log_event("step_end", step=2, name="permission_and_execute", duration_seconds=time.time() - start_time)
            log("Step 2 complete. State saved.")
        finalize_run()
        print("\n" + state["final_summary"], flush=True)
        return 0
    except SystemExit as e:
        finalize_run()
        return e.code or 1
    except Exception as e:
        log(f"Fatal error: {e}")
        log_exception(e)
        finalize_run()
        return 1

if __name__ == "__main__":
    raise SystemExit(main())