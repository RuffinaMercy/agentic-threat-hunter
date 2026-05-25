[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

# Agentic AI Skill Marketplace Security Demo

> **A stateful AI news agent that loads skills from a local marketplace and demonstrates supply‑chain attacks with three layers of defense: cryptographic signing, policy‑as‑code, and Docker sandboxing.**

## What It Does

The agent fetches daily AI news, loads JSON skills from `skills/`, selects a skill by rating/downloads, checks policy and user approval, then executes either a Groq text skill or a Docker‑sandboxed code skill.

## Quick Start

```bash
# Clone the repository
git clone https://github.com/RuffinaMercy/agentic-threat-hunter.git
cd agentic-threat-hunter

# Create virtual environment and install dependencies
python -m venv .venv
source .venv/bin/activate       # Linux/macOS
.venv\Scripts\activate          # Windows

pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your GROQ_API_KEY (and optional SKILL_SIGNING_KEY)

# (Optional) Build Docker sandbox for code skills
docker build -t skill-sandbox .

# Run the secure agent
python agent.py

# Run attack demo (bypass signature verification)
rm agent_state.json              # or Remove-Item on Windows
python agent.py --skip-verification

# Launch Streamlit observability dashboard
streamlit run ui.py
# Opens http://localhost:8501
```

## Project Map

- `agent.py` – backend agent, state machine, skill loading, policy enforcement, execution  
- `ui.py` – Streamlit dashboard (run agent, view skills, logs, metrics, policies)  
- `skills/` – local marketplace skills (JSON files)  
- `policies.yaml` – policy‑as‑code rules (allow/deny/approval requirements)  
- `logger.py` – JSONL audit logging and SQLite SRE metrics  
- `sandbox_docker.py` – Docker wrapper for code skills  
- `sign_skill.py` / `sign_all_skills.py` – HMAC‑SHA256 skill signing  
- `agent_state.json` – generated resumable state (excluded from git)  
- `logs/agent_logs.jsonl` – structured audit logs (excluded)  
- `logs/metrics.db` – SQLite metrics database (excluded)  

## Setup Details

### Environment Variables (`.env`)

```ini
GROQ_API_KEY=your_groq_key_here
SKILL_SIGNING_KEY=optional_32_byte_hex_key
```

If `SKILL_SIGNING_KEY` is empty, `sign_skill.py` can generate one automatically.

### Docker Requirement (for Code Skills)

Code skills execute inside a Docker sandbox for isolation.  
- Install [Docker Desktop](https://www.docker.com/products/docker-desktop/) (Windows/macOS) or native Docker (Linux).  
- On Windows, enable WSL2 backend.  
- Verify with:  
  ```bash
  docker run --rm python:3.11-slim python -c "print('docker ok')"
  ```

## Running the Agent

| Command | Description |
|---------|-------------|
| `python agent.py` | Normal secure mode – only signed skills load. |
| `python agent.py --skip-verification` | Attack demo – loads all skills (unsigned allowed). |
| `rm agent_state.json` (or `Remove-Item`) | Reset state before a fresh run. |

The agent is **resumable** – it saves progress to `agent_state.json`. If today’s run is already marked `done`, it prints the cached summary.

## 📊 Observability Dashboard

Launch the UI with `streamlit run ui.py`. Tabs:

- **Run Agent** – execute the agent and watch live logs.
- **Latest Summary** – final summary from the last run.
- **Raw News** – fetched headlines grouped by source.
- **Skill Marketplace** – browse skills, ratings, downloads, signature status.
- **Observability** – advanced monitoring:
  - **Audit Logs** – JSONL event viewer with filtering and export.
  - **Metrics** – tokens, steps, errors, duration.
  - **Trends** – Plotly charts (tokens/run, errors over time).
  - **Policy Editor** – live YAML editing with validation.

## Skills & Attack Demo

### Marketplace Simulation

Skills are JSON files with `name`, `description`, `rating`, `downloads`, and either `instructions` (text) or `code` (Python).  
The selector is intentionally naive: **highest rating wins; downloads break ties**. This mimics a marketplace that over‑trusts popularity signals.

### Attack Demonstration

1. Reset state: `rm agent_state.json`
2. Run with `--skip-verification`: `python agent.py --skip-verification`
3. Agent loads all skills, selects the **highest‑rated** skill (e.g., `malicious_code_skill` rating 5.0).
4. Permission gate displays the skill’s instructions or code preview (base64 text is decoded before display).
5. Approve execution (`yes`).
6. Outcome:
   - **Text skill** → LLM produces biased summary with forced phrase `"Experts warn of catastrophic risk"`.
   - **Code skill** → Docker sandbox blocks `rm -rf /` and returns a read‑only filesystem error.

### Policy Enforcement

Edit `policies.yaml` to set `allowed: false` for a skill. The skill is then denied immediately without asking for approval.

## Signing Skills (Integrity)

- Sign one skill: `python sign_skill.py skills/standard_summarizer.json`
- Sign all skills: `python sign_all_skills.py`

Signing uses **HMAC‑SHA256** over canonical JSON. Any modification after signing invalidates the signature, and the agent rejects the skill (unless `--skip-verification` is used).  
*Security note:* HMAC uses a shared secret; production systems would use asymmetric keys (Ed25519).

## Tests

Run the integrity and policy tests:

```bash
pytest test_agent.py -v
```

Expected output:

```
test_agent.py::test_signature_verification PASSED
test_agent.py::test_policy_blocks_denied_skill PASSED
test_agent.py::test_policy_allows_with_approval PASSED
```

## Threat Model & Mitigations

| Attack | Mitigation |
|--------|-------------|
| Malicious skill injection | HMAC signatures reject unsigned/modified skills |
| Prompt injection (base64 encoded) | Decode before display/execution |
| Arbitrary code execution | Docker sandbox (no network, read‑only FS, non‑root user) |
| Unauthorised skill execution | Policy‑as‑code (`allowed` / `require_approval`) |
| Human‑in‑the‑loop bypass | Permission gate (explicit `yes` required) |
| Lack of auditability | JSONL logs + SQLite metrics + Streamlit dashboard |

## ⚠️ Known Limitations

- **Docker required** for code skills; text‑only mode works without it.
- **Symmetric signing** – HMAC uses a shared secret; production would use asymmetric keys.
- **Human approval burden** – automated risk scoring is future work.
- **Intentional unsafe selection** – popularity‑based selection is deliberately naive for demo purposes.
- **Local prototype** – not a multi‑tenant marketplace; no authentication or network hardening.

## 📄 License

MIT – see [LICENSE](LICENSE) file.


## 📚 Additional Documentation

- [Architecture Overview](docs/architecture.md) – detailed flowchart and component descriptions.
- [Demo Walkthrough](docs/demo.md) – step‑by‑step screenshots of normal mode, attack, policy, and observability.
```

