[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![Live Demo](https://img.shields.io/badge/Live_Demo-Streamlit-FF4B4B?style=for-the-badge&logo=Streamlit&logoColor=white)](https://ruffina-ai-news-agent.streamlit.app/)
[![Security Research](https://img.shields.io/badge/Security-Research-red)](research/04-scanner-reports/supply-chain-attack-analysis.md)

# Agentic AI – Security Research Edition

> **From threat model to mitigation: supply‑chain attacks, indirect prompt injection (T6), and layered defences for an AI news agent.**

This repository started as a stateful AI news agent. It evolved into a **complete AI security research project** covering two critical OWASP threats:

- **LLM03:2025 – Supply Chain Vulnerabilities** (skill marketplace poisoning, HMAC key compromise)
- **LLM01:2025 – Prompt Injection (T6: Intent Breaking & Goal Manipulation)**

We simulate real attacks, then implement **defence in depth** using industry‑grade mitigations: HMAC signing, keyring, Cisco Skill Scanner, Llama 3.1 classification, quarantine, trust boundaries, and output validation.

---

## 🎯 Live Demo (Original Agent)

[![Live Demo](https://img.shields.io/badge/Live_Demo-Streamlit-FF4B4B?style=for-the-badge&logo=Streamlit&logoColor=white)](https://ruffina-ai-news-agent.streamlit.app/)

The live demo runs the **secure agent** – it fetches daily AI news, selects the highest‑rated skill, and produces a summary.  
*To see the full security research (attack simulations, T6 mitigations, scanner reports), clone the repository.*

---

## 🧠 Research Summary (Two Threat Streams)

### 1. Supply‑Chain Attack (Skill Marketplace)

| Phase | What was done | Key Output |
|-------|---------------|-------------|
| **Threat modelling** | MAESTRO framework, attack tree for “Tool Misuse” | [Diagrams](research/01-threat-modelling/) |
| **Attack simulation** | Stole HMAC key from `.env`, signed a malicious skill | [Simulation script](research/02-attack-simulation/simulate_key_compromise.py) |
| **Mitigation #1** | Moved signing key to Windows Credential Manager (`keyring`) | [Keyring implementation](research/03-mitigations/keyring-implementation.md) |
| **Mitigation #2** | Integrated Cisco Skill Scanner (blocks CRITICAL/HIGH) | [Scanner reports](research/04-scanner-reports/) |

### 2. Indirect Prompt Injection (T6 – Intent Breaking)

| Phase | What was done | Key Output |
|-------|---------------|-------------|
| **Threat understanding** | Indirect injection via news articles (leetspeak, plain commands) | [T6 research doc](research/T6_Intent_Breaking_Indirect_Prompt_Injection.md) |
| **Attack simulation** | Malicious `agent_state.json` with plain & obfuscated injections | [Example](screenshots/attack.png) |
| **Mitigations** | Llama 3.1 input guard, quarantine, trust labels, prompt isolation, output validation | Code in `agent/security/` |
| **Evaluation** | 0% false positives on real news, 100% detection of both injection variants | [Evaluation details](research/T6_Intent_Breaking_Indirect_Prompt_Injection.md#5-evaluation) |

**Full analysis:**  
- [`supply-chain-attack-analysis.md`](research/04-scanner-reports/supply-chain-attack-analysis.md)  
- [`T6_Intent_Breaking_Indirect_Prompt_Injection.md`](research/T6_Intent_Breaking_Indirect_Prompt_Injection.md)

---

## 📁 Project Structure (Updated)

```
.
├── agent/                         # Core agent code
│   ├── security/                  # Security layers (T6 mitigations)
│   │   ├── inputs.py              # Llama 3.1 classifier + quarantine
│   │   └── outputs.py             # Output validation
│   ├── agent.py                   # Main agent (HMAC, scanner, keyring, T6 layers)
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
│   ├── 01-threat-modelling/       # Diagrams, attack tree
│   ├── 02-attack-simulation/      # Key compromise script
│   ├── 03-mitigations/            # Implementation docs
│   ├── 04-scanner-reports/        # Scanner outputs
│   └── T6_Intent_Breaking_Indirect_Prompt_Injection.md  # New T6 research
├── screenshots/                   # Images for README and T6 doc
├── tests/                         # Unit/integration tests
├── docs/                          # Architecture & walkthrough
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
- Groq API key (free tier)

### Installation

```bash
git clone https://github.com/RuffinaMercy/agentic-threat-hunter.git
cd agentic-threat-hunter

python -m venv .venv
source .venv/bin/activate       # Linux/macOS
.venv\Scripts\activate          # Windows

pip install -r requirements.txt

# Install Cisco Skill Scanner (for supply‑chain mitigation)
pip install cisco-ai-skill-scanner

# Set up environment variables
cp .env.example .env
# Edit .env with your GROQ_API_KEY (and optionally HF_TOKEN, not required for T6)

# (Optional) Build Docker sandbox
docker build -t skill-sandbox .
```

### 🔑 Storing the HMAC Key (Supply‑Chain Mitigation)

The agent no longer reads the signing key from `.env`. Store it once using `keyring`:

```bash
python -c "import keyring; keyring.set_password('skill_marketplace', 'SKILL_SIGNING_KEY', 'your_hex_key_here')"
```

Generate a random 32‑byte hex key with:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

### Running the Secured Agent (with all T6 mitigations)

```bash
cd agent
python agent.py
```

The agent will:
1. Fetch news.
2. **Apply T6 input guard** (Llama 3.1 classifies each news item as SAFE/UNSAFE).
3. **Quarantine suspicious** articles (reported to user).
4. Load skills, run Cisco scanner, verify HMAC signatures.
5. Enforce policy & human approval.
6. Execute the selected skill with **trust boundaries** (`<NEWS_DATA>` + extraction framing).
7. Perform **output validation** (dangerous commands, unexpected URLs).
8. Show final summary + quarantine report.

### Running the Attack Simulations

- **Supply‑chain attack (key compromise):**  
  ```bash
  python agent/simulate_key_compromise.py
  ```

- **T6 indirect prompt injection:**  
  Place the malicious `agent_state.json` (see [research/T6...](research/T6_Intent_Breaking_Indirect_Prompt_Injection.md)) in `data/` and run `python agent.py`.

---

## 📊 Observability Dashboard

```bash
streamlit run agent/ui.py
```

Tabs include: Run Agent, Latest Summary, Raw News, Skills, Observability, Policy Editor.

---

## 🧪 Testing

```bash
pytest test_agent.py -v
```

---

## 🛡️ Defence in Depth – Combined Layers

| Layer | Technology | Threat Addressed |
|-------|------------|------------------|
| **1. Input guard** | Llama 3.1 classifier (Groq) | Indirect prompt injection (T6) |
| **2. Quarantine & provenance** | Trust labels, persistent state | Suspicious content isolation |
| **3. Prompt isolation** | `<NEWS_DATA>` delimiters + extraction framing | Goal manipulation |
| **4. Output validation** | Dangerous commands + URL checks | Residual manipulation |
| **5. Pre‑execution scanning** | Cisco Skill Scanner | Malicious skills (supply chain) |
| **6. Integrity** | HMAC‑SHA256 signing | Tampered skills |
| **7. Secrets management** | Keyring (Windows Credential Manager) | Key theft |
| **8. Policy & approval** | YAML policies + human gate | Unauthorised execution |
| **9. Runtime isolation** | Docker sandbox | Arbitrary code execution |
| **10. Observability** | JSONL logs + SQLite metrics | Audit & anomaly detection |

---

## 🔗 Framework Mapping

| Threat | OWASP | MITRE ATLAS | Mitigation |
|--------|-------|-------------|-------------|
| Malicious skill with fake rating | LLM03 | T1199 | Cisco scanner |
| HMAC key in plaintext | LLM06 | T1552 | Keyring |
| Indirect prompt injection (T6) | LLM01 | AML.T0059 | Llama 3.1 input guard + quarantine + prompt isolation |
| Output manipulation | LLM01 | AML.T0059 | Output validation |

---

## 📚 Key Documentation

- [Supply‑chain attack analysis](research/04-scanner-reports/supply-chain-attack-analysis.md)
- [T6 – Indirect prompt injection (Intent Breaking)](research/T6_Intent_Breaking_Indirect_Prompt_Injection.md)
- [Threat modelling (MAESTRO)](research/01-threat-modelling/threat-modelling-process.md)
- [Keyring implementation](research/03-mitigations/keyring-implementation.md)
- [Cisco scanner integration](research/03-mitigations/cisco-scanner-integration.md)

---

## ⚠️ Limitations & Future Work

- **T6 input guard** uses Groq’s cloud API – requires internet; offline version possible with local models (future work).  
- **Keyring** works on Windows out‑of‑the‑box; Linux/macOS may need additional backends.  
- **Scanner behavioural analysis** requires LLM API key (optional).  
- **No key rotation** – static HMAC keys could be rotated periodically.  
- **User approval fatigue** – future UI could rate‑limit or hash display.

---

## 🤝 Acknowledgements

- [Cisco AI Defense](https://github.com/cisco-ai-defense/skill-scanner)
- [OWASP Agentic AI Initiative](https://owasp.org/www-project-agentic-ai/)
- [Groq](https://groq.com) for free LLM inference
- [AI Red Teaming Guide](https://github.com/requie/AI-Red-Teaming-Guide)

---
