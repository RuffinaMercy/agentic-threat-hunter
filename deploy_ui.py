import json
import os
import subprocess
import sys
from datetime import date
from pathlib import Path

import streamlit as st

BASE_DIR = Path(__file__).resolve().parent
STATE_FILE = BASE_DIR / "agent_state.json"
AGENT_FILE = BASE_DIR / "agent.py"
STARRED_FILE = BASE_DIR / "starred_news.json"

def read_state():
    if not STATE_FILE.exists():
        return {}
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return {}

def save_state(state):
    STATE_FILE.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")

def format_date(d: date):
    return d.strftime("%d/%m/%Y")

def load_starred():
    if not STARRED_FILE.exists():
        return []
    try:
        data = json.loads(STARRED_FILE.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except:
        return []

def save_starred(starred_list):
    STARRED_FILE.write_text(json.dumps(starred_list, indent=2, ensure_ascii=False), encoding="utf-8")

def truncate(text, max_len=200):
    if len(text) <= max_len:
        return text
    return text[:max_len] + "..."

def render_news_with_stars(state, starred_items):
    if state.get("final_summary"):
        st.subheader("📰 Today’s Summary")
        st.markdown(state["final_summary"])
    else:
        st.info("No summary yet. Click 'Run Agent' to generate today’s briefing.")

    raw_news = state.get("raw_news") or []
    item_summaries = state.get("item_summaries", {})
    if raw_news:
        st.subheader(f"📌 Live News Links ({len(raw_news)})")
        for idx, item in enumerate(raw_news):
            title = item.get("title") or "Untitled"
            source = item.get("source") or "Unknown source"
            url = item.get("url")
            # Use LLM‑generated summary if available, else fallback
            short_summary = item_summaries.get(title, "")
            if not short_summary:
                summary = item.get("summary") or ""
                short_summary = truncate(summary, 200) if summary else "No summary available."

            item_key = f"{source}_{title}_{url}" if url else f"{source}_{title}"
            is_starred = any(s.get("key") == item_key for s in starred_items)

            with st.container():
                cols = st.columns([0.85, 0.15])
                with cols[0]:
                    st.markdown(f"**{title}**")
                    st.caption(short_summary)
                    if url:
                        st.markdown(f"*{source}* · [Read full →]({url})")
                    else:
                        st.markdown(f"*{source}*")
                with cols[1]:
                    star_btn = "⭐" if is_starred else "☆"
                    if st.button(star_btn, key=f"star_{idx}_{item_key}", help="Bookmark this news"):
                        if is_starred:
                            starred_items = [s for s in starred_items if s.get("key") != item_key]
                            st.toast(f"Removed star from '{title[:60]}'")
                        else:
                            starred_items.append({
                                "key": item_key,
                                "title": title,
                                "source": source,
                                "url": url,
                                "date": state.get("date", date.today().isoformat())
                            })
                            st.toast(f"⭐ Starred '{title[:60]}'")
                        save_starred(starred_items)
                        st.rerun()
                st.divider()
    else:
        st.info("No news items fetched yet. Run the agent to fetch today’s news.")

st.set_page_config(page_title="AI News Agent", layout="wide", page_icon="🤖")
st.title("🤖 AI News Agent")
st.caption(f"Today’s date: **{format_date(date.today())}** · Secure mode (signed skills only)")

with st.sidebar:
    st.header("⭐ Bookmarked News")
    starred = load_starred()
    if starred:
        for i, item in enumerate(starred):
            st.markdown(f"**{item.get('title', 'Untitled')}**")
            st.caption(f"Source: {item.get('source', '?')} · Date: {item.get('date', '?')}")
            if item.get("url"):
                st.markdown(f"[Read full →]({item['url']})")
            if st.button("Remove star", key=f"rm_star_{i}"):
                new_starred = [s for s in starred if s.get("key") != item.get("key")]
                save_starred(new_starred)
                st.rerun()
            st.divider()
    else:
        st.info("☆ Click the star icon on any news to bookmark it here.")

current_state = read_state()
if current_state and current_state.get("done") and current_state.get("date") == date.today().isoformat():
    render_news_with_stars(current_state, load_starred())
else:
    st.info("No briefing for today. Click 'Run Agent' to generate one.")

col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    run_btn = st.button("▶ Run Agent (Secure Mode)", type="primary", use_container_width=True)

if run_btn:
    with st.spinner("Agent is running – fetching news and generating summary..."):
        cmd = [sys.executable, str(AGENT_FILE)]
        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"
        env["AGENT_APPROVE_SKILL"] = "yes"
        try:
            result = subprocess.run(cmd, cwd=str(BASE_DIR), env=env, capture_output=True, text=True, timeout=180)
            logs = (result.stdout or "") + (result.stderr or "")
            with st.expander("Agent logs (click to expand)"):
                st.code(logs or "Agent finished without output.", language="text")
            if result.returncode == 0:
                st.success("Agent run completed. Refresh below.")
                st.rerun()
            else:
                st.error(f"Agent failed with exit code {result.returncode}.")
        except subprocess.TimeoutExpired as exc:
            st.error("Agent execution timed out after 180 seconds.")
            with st.expander("Timeout details"):
                st.code(str(exc), language="text")
        except Exception as exc:
            st.error(f"Error: {exc}")

st.markdown("---")
st.caption("Secure demo – only signed text skills. Code skills are not executed in this live version. Star any news to bookmark it.")