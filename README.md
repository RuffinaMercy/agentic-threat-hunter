[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![Live Demo](https://img.shields.io/badge/Live_Demo-Streamlit-FF4B4B?style=for-the-badge&logo=Streamlit&logoColor=white)](https://ruffina-ai-news-agent.streamlit.app/)
[![Security Research](https://img.shields.io/badge/Security-Research-red)](research/04-scanner-reports/supply-chain-attack-analysis.md)

# Agentic AI Skill Marketplace – Security Research Edition

> **From threat model to mitigation: a fully documented supply‑chain attack simulation against an AI news agent, with layered defenses including HMAC signing, keyring, and Cisco Skill Scanner.**

This repository started as a stateful AI news agent. It evolved into a **complete AI security research project** that:

- Maps threats using the **MAESTRO 7‑layer framework**
- Simulates an **HMAC key compromise** (stealing the signing key from `.env`)
- Implements **two industry‑grade mitigations**: secrets management (`keyring`) and pre‑execution scanning (Cisco Skill Scanner)
- Validates the mitigations against real malicious skills (prompt injection, command injection)

---

## 🎯 Live Demo (Original Agent)

[![Live Demo](https://img.shields.io/badge/Live_Demo-Streamlit-FF4B4B?style=for-the-badge&logo=Streamlit&logoColor=white)](https://ruffina-ai-news-agent.streamlit.app/)

The live demo runs the **secure agent** without the attack simulation – it fetches daily AI news, selects the highest‑rated skill, and summarises the results.  
*To see the full security research (threat model, key compromise, scanner integration), clone the repository and follow the instructions below.*

---

## 🧠 Research Summary

| Phase | What was done | Key Output |
|-------|---------------|-------------|
| **Threat modelling** | Drew data flow diagram, built attack tree for “Tool Misuse”, mapped to MAESTRO layers | [Diagrams & process](research/01-threat-modelling/) |
| **Attack simulation** | Stole HMAC key from `.env`, signed a malicious skill, agent executed it | [Simulation script](research/02-attack-simulation/simulate_key_compromise.py) |
| **Mitigation #1** | Moved signing key from `.env` to Windows Credential Manager (`keyring`) | [Keyring implementation](research/03-mitigations/keyring-implementation.md) |
| **Mitigation #2** | Integrated Cisco Skill Scanner to block CRITICAL/HIGH findings before HMAC | [Scanner integration](research/03-mitigations/cisco-scanner-integration.md) |
| **Validation** | Ran scanner on `malicious_code_skill` (HIGH) and `malicious_text_skill` (CRITICAL) – both blocked | [Scanner reports](research/04-scanner-reports/) |

**Full analysis:** [`supply-chain-attack-analysis.md`](research/04-scanner-reports/supply-chain-attack-analysis.md)

---

## 📁 Project Structure

```
.
├── agent/                         # Core agent code
│   ├── agent.py                   # Main agent (HMAC + scanner + keyring)
│   ├── logger.py                  # Audit logging & metrics
│   ├── sandbox_docker.py          # Docker sandbox wrapper
│   ├── sign_skill.py              # Sign a single skill (uses keyring)
│   ├── sign_all_skills.py         # Sign all skills (uses keyring)
│   ├── policies.yaml              # Policy‑as‑code
│   ├── ui.py                      # Streamlit dashboard
│   └── store_key.py               # One‑time key storage in keyring
├── skills/                        # JSON marketplace skills
├── data/                          # Persistent state (agent_state.json, etc.)
├── logs/                          # JSONL logs & SQLite metrics
├── research/                      # All threat modelling & security research
│   ├── 01-threat-modelling/       # Diagrams, attack tree, process
│   ├── 02-attack-simulation/      # Key compromise script
│   ├── 03-mitigations/            # Implementation documentation
│   └── 04-scanner-reports/        # Scanner outputs & final analysis
├── tests/                         # Unit/integration tests
├── docs/                          # Architecture & demo walkthrough
├── .env.example                   # Environment template (no secrets)
├── requirements.txt
└── Dockerfile                     # Sandbox container
```

---

## 🚀 Local Setup (Full Research Version)

### Prerequisites

- Python 3.10+
- Docker Desktop (for code skills)
- Git
- (Windows) no extra tools – keyring uses native Credential Manager

### Installation

```bash
# Clone the repository
git clone https://github.com/RuffinaMercy/agentic-threat-hunter.git
cd agentic-threat-hunter

# Create virtual environment
python -m venv .venv
source .venv/bin/activate       # Linux/macOS
.venv\Scripts\activate          # Windows

# Install dependencies
pip install -r requirements.txt

# Install Cisco Skill Scanner (for pre‑execution scanning)
pip install cisco-ai-skill-scanner

# Set up environment variables
cp .env.example .env
# Edit .env with your GROQ_API_KEY (and optionally SKILL_SIGNING_KEY – see below)

# (Optional) Build Docker sandbox
docker build -t skill-sandbox .
```

### 🔑 Storing the HMAC Key in Windows Credential Manager

The agent no longer reads the key from `.env`. Instead, store it once using `keyring`:

```bash
python -c "import keyring; keyring.set_password('skill_marketplace', 'SKILL_SIGNING_KEY', 'your_hex_key_here')"
```

You can generate a random 32‑byte hex key with:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

If you skip this step, the agent will raise an error – that’s intentional to force secure key storage.

### Running the Secured Agent

```bash
cd agent
python agent.py
```

The agent will:
1. Fetch news.
2. Load skills.
3. **Run Cisco Skill Scanner** on each skill – any `CRITICAL` or `HIGH` finding blocks the skill.
4. Verify HMAC signature (using key from keyring).
5. Ask for approval (if policy requires).
6. Execute the highest‑rated safe skill.

### Running the Attack Simulation (Old vulnerable version)

To see the original vulnerability (key in `.env`, no scanner):

```bash
# Temporarily put the key in .env (not recommended for production)
echo "SKILL_SIGNING_KEY=your_hex_key" >> .env
python agent/simulate_key_compromise.py   # runs the attack script
```

The simulation will steal the key, sign a malicious skill, and the agent will execute it.

---

## 📊 Observability Dashboard

Launch the Streamlit UI from the `agent/` folder:

```bash
streamlit run ui.py
```

Tabs include:
- **Run Agent** – execute and watch logs.
- **Latest Summary** – cached summary.
- **Raw News** – fetched headlines.
- **Skill Marketplace** – browse skills, ratings, signatures.
- **Observability** – audit logs, metrics, trends, policy editor.

---

## 🧪 Testing

```bash
pytest test_agent.py -v
```

Tests cover signature verification, policy enforcement, and approval gates.

---

## 🛡️ Security Layers (Defence in Depth)

| Layer | Technology | What It Stops |
|-------|------------|----------------|
| **1. Pre‑execution scanning** | Cisco Skill Scanner (YARA rules) | Prompt injection, command injection, malicious patterns |
| **2. Integrity** | HMAC‑SHA256 signing | Tampered or unapproved skills |
| **3. Secrets management** | Keyring (Windows Credential Manager) | Key theft from `.env` or Git history |
| **4. Policy & approval** | YAML policies + human gate | Unauthorised skill execution |
| **5. Runtime isolation** | Docker sandbox (read‑only FS, no network) | Arbitrary code execution |
| **6. Observability** | JSONL logs + SQLite metrics | Audit trail, anomaly detection |

---

## 🔗 Framework Mapping

| Threat | OWASP LLM 2025 | MITRE ATLAS | Mitigation |
|--------|----------------|-------------|-------------|
| Malicious skill with fake rating | LLM03: Supply Chain | T1199 | Cisco scanner |
| HMAC key in plaintext | LLM06: Sensitive Info Disclosure | T1552 | Keyring |
| User approval fatigue | LLM07: Insecure Plugin Design | T1204 | Human gate (future: throttling) |
| Indirect prompt injection (RSS) | LLM01: Prompt Injection | AML.T0059 | Not yet mitigated (future work) |

---

## 📚 Documentation

- [Full research analysis](research/04-scanner-reports/supply-chain-attack-analysis.md)
- [Threat modelling process (MAESTRO)](research/01-threat-modelling/threat-modelling-process.md)
- [Keyring implementation](research/03-mitigations/keyring-implementation.md)
- [Cisco scanner integration](research/03-mitigations/cisco-scanner-integration.md)
- [Original architecture overview](docs/architecture.md)
- [Demo walkthrough](docs/demo.md)

---

## ⚠️ Limitations & Future Work

- **Keyring only on Windows** – the code works cross‑platform but was tested on Windows; Linux/macOS would use `keyring` backends.
- **Scanner static only** – behavioural scanning (`--use-behavioral`) requires an LLM API key (planned).
- **No key rotation** – keys are static; rotation would improve security.
- **Indirect prompt injection** – RSS feeds are not sanitised (future enhancement).
- **Approval fatigue** – no throttling or hash display (future UI improvement).

---

## 🤝 Acknowledgements

- [Cisco AI Defense](https://github.com/cisco-ai-defense/skill-scanner) for the skill scanner
- [AI Red Teaming Guide](https://github.com/requie/AI-Red-Teaming-Guide) for attack trees
  
---
