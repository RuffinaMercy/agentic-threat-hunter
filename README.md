[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

# Agentic AI Skill Marketplace Security Demo

> **A stateful AI agent that fetches daily news, loads skills from a local marketplace, and demonstrates supply-chain attacks with three layers of defense: cryptographic signing, policy-as-code, and Docker sandboxing.**

## What It Does

The agent fetches daily AI news, loads JSON skills from `skills/`, selects a skill by rating/downloads for demo purposes, checks policy and user approval, then executes either a Groq text skill or a Docker-sandboxed code skill.

## Quick Start

```powershell
# Clone and activate environment
git clone https://github.com/yourusername/agentic-threat-hunter.git
cd agentic-threat-hunter
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

# Configure credentials
Copy-Item .env.example .env
# Edit .env with your GROQ_API_KEY and SKILL_SIGNING_KEY

# Build Docker sandbox image (optional, for code skills)
docker build -t skill-sandbox .

# Run the secure agent
python agent.py

# Run attack demo (skip signature verification)
Remove-Item agent_state.json
python agent.py --skip-verification

# Launch Streamlit observability dashboard
streamlit run ui.py
# Opens: http://localhost:8501
```

## Project Map

- `agent.py` - backend agent, state machine, skill loading, policy enforcement, signing checks, execution
- `ui.py` - Streamlit dashboard for running the agent, viewing skills, logs, metrics, and policies
- `skills/` - local marketplace skills
- `policies.yaml` - policy-as-code rules for allowed skills and approval requirements
- `logger.py` - JSONL audit logging and SQLite SRE metrics
- `sandbox_docker.py` - Docker-backed code execution wrapper
- `sign_skill.py` - signs one skill with HMAC-SHA256
- `sign_all_skills.py` - signs all skill JSON files
- `agent_state.json` - generated resumable state
- `logs/agent_logs.jsonl` - generated structured audit logs
- `logs/metrics.db` - generated SQLite metrics database

## Setup

```powershell
cd "c:\Users\Ruffina\Desktop\Interests\Skill Marketplace Poisoning"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Edit `.env`:

```text
GROQ_API_KEY=your_groq_key_here
SKILL_SIGNING_KEY=
```

If `SKILL_SIGNING_KEY` is empty, `sign_skill.py` can generate one automatically.

### Docker Requirement for Code Skills

Code skills execute through Docker for isolation. **On Windows:**

- Install Docker Desktop
- Enable WSL2 backend in Docker Desktop settings
- Start Docker Desktop before running code-skill demos
- Verify Docker works:

```powershell
docker run --rm python:3.11-slim python -c "print('docker ok')"
```

If Docker is unavailable, text skills continue to work; code skills return a sandbox error.

## Run the Agent

Normal signed-skill mode:

```powershell
python agent.py
```

Demo mode that loads unsigned skills:

```powershell
python agent.py --skip-verification
```

Reset state before a fresh demo:

```powershell
Remove-Item agent_state.json
```

The agent is resumable. If `agent_state.json` says today is already `done`, it prints the stored summary and skips fetching/selection.

## Run the UI

```powershell
streamlit run ui.py
```

Open: `http://localhost:8501`

For demo convenience, the UI launches the agent with `--skip-verification`, so unsigned attack-demo skills can participate.

## 🖥️ Observability Dashboard

The Streamlit UI provides:

- **Run Agent** – Execute the agent with live output
- **Latest Summary** – View the most recent run's news summary
- **Raw News** – Inspect fetched headlines and metadata
- **Skill Marketplace** – Browse available skills, ratings, and signatures
- **🔍 Observability** – Advanced monitoring:
  - **Audit Logs** – JSONL event viewer with type/run-ID filtering, JSON export
  - **Metrics** – Latest run summary (tokens, steps, errors, duration)
  - **Trends** – Plotly charts: tokens/run, steps/run, errors over time
  - **Policy Editor** – Live YAML editing with syntax validation and reload button

## Skills

Current demo skills use clear names:

- `Standard Summarizer` - legitimate text summarizer
- `benign_code_news_fetcher` - benign code skill
- `benign_code_summarizer` - benign code skill
- `malicious_text_skill_encoded` - base64-encoded prompt-injection demo
- `malicious_text_skill_plain` - plain prompt-injection demo created by the UI
- `malicious_code_skill` - destructive-code demo run inside Docker sandbox

The selector is intentionally deterministic for the demo:

```text
highest rating wins; downloads break ties
```

This mimics a marketplace that over-trusts popularity signals.

## Signing Skills

Sign one skill:

```powershell
python sign_skill.py skills\standard_summarizer.json
```

Sign all skills:

```powershell
python sign_all_skills.py
```

Signing uses HMAC-SHA256 over canonical JSON. Any edit after signing invalidates the signature.

Security note: signing proves the file was approved by someone with the signing key. It does not prove the content is safe.

## 🧪 Tests

Verify agent integrity and policy enforcement:

```powershell
pytest test_agent.py -v
```

Expected output:

```
test_agent.py::test_signature_verification PASSED
test_agent.py::test_policy_blocks_denied_skill PASSED
test_agent.py::test_policy_allows_with_approval PASSED
```

## Policy-as-Code

`policies.yaml` controls which skills can run:

```yaml
default_behavior: ask
max_steps: 10

skills:
  - name: Standard Summarizer
    allowed: true
    require_approval: true

sandbox:
  timeout: 15
  memory_limit: 128m
```

Policy decisions happen before execution. A denied skill is blocked before the user prompt.

## 🧪 Attack Demo (What a Recruiter Will See)

**Goal:** Demonstrate that popularity-based skill selection is unsafe and how mitigations defend against it.

1. **Reset state** (fresh run):
   ```powershell
   Remove-Item agent_state.json
   ```

2. **Run with signature bypass** (to simulate marketplace with unsigned skills):
   ```powershell
   python agent.py --skip-verification
   ```

3. **Agent fetches daily AI news** and lists available skills

4. **Agent selects highest-rated skill automatically**
   - `malicious_code_skill` (rating: 5.0, downloads: 999) – *wins*
   - or `malicious_text_skill_encoded` (rating: 4.95, downloads: 20000) if code skill blocked by policy

5. **Permission gate displays the malicious instruction or code**
   - Base64-encoded text is **decoded before display** for human review
   - Code is shown as a preview before execution
   - User must explicitly approve: `Execute this skill? (yes/no):`

6. **If approved**, observe the attack:
   - **Text skill outcome** → Summary contains forced bias phrase *"Experts warn of catastrophic risk"* injected into every bullet point
   - **Code skill outcome** → Docker sandbox blocks `rm -rf /` system command and returns a read-only filesystem error (attack contained)

7. **Audit logs and metrics recorded** → View in observability dashboard

**Key insight:** Without mitigations, the agent would blindly execute the highest-rated skill. With signing, policy, gates, and logging, even if the attacker wins the popularity contest, the system detects and logs the attempt.

## Threat Model

This project models a local skill marketplace where attackers may try to:

- add a new malicious skill
- edit a trusted skill after signing
- hide instructions with base64 encoding
- inflate rating/download metadata
- submit code that attempts filesystem or network abuse
- exploit weak approval flows

## Mitigations Demonstrated

- HMAC signatures reject unauthorized skill file changes.
- Policy-as-code centrally allows, denies, or requires approval.
- Permission gate shows instructions or code before execution.
- Base64-looking instructions are decoded before display/execution.
- Docker sandbox isolates code skills from the host.
- Structured logs provide audit evidence.
- SQLite metrics track runs, errors, tokens, steps, and code execution.
- Streamlit observability helps inspect behavior quickly.

## ⚠️ Known Limitations & Production Gaps

- **Dependency on Docker** – Code skills require Docker Desktop (Windows/WSL2) or native Docker. Text-only mode works without it.
- **Symmetric signing** – HMAC uses a shared secret; production would use asymmetric keys (Ed25519) to prevent key leakage risks.
- **Human approval burden** – Policy gates still rely on user vigilance; automated risk scoring is future work.
- **Intentional unsafe selection** – Popularity-based selection is deliberately naive to demonstrate the attack surface.
- **Local prototype** – Not a multi-tenant marketplace; no authentication, RBAC, or network hardening.

## 📄 License

MIT – see [LICENSE](LICENSE) file.

## 🙏 Acknowledgments

Inspired by Anthropic's Agent Skills research and Microsoft's Agent Governance Toolkit. Built as a security research prototype to understand supply-chain risks in agentic systems.


