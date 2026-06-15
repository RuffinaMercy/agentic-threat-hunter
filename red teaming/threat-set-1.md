
# Threat Set #1: Tool Misuse (Supply Chain + Human Approval)

> **Researcher**: Ruffina Mercy  
> **Timeline**: May 30 – June 1, 2026  
> **Target Agent**: AI news summarizer with skill marketplace  
> **Framework alignment**: OWASP LLM Top 10 2025, MITRE ATLAS, MAESTRO 7‑layer threat model  

---

## 📌 Executive Summary

I built a threat model for my AI news agent, identifying **supply chain attacks** as a critical risk (malicious skills with fake ratings, HMAC key compromise, approval fatigue). Then I validated those threats using **Cisco Skill Scanner** – an industry tool for analysing AI agent skills. The scanner confirmed that my malicious test skills (command injection and prompt injection) are detected at **HIGH** and **CRITICAL** severity levels, while benign skills pass as **SAFE**.

This work bridges my original threat analysis with real‑world security tooling, proving that I can think like an attacker and use professional tools to defend.

---

## 🎯 Why I Did This

My agent loads “skills” (JSON packages with code and instructions) from a marketplace. Attackers could upload a skill with a **5‑star rating** that contains hidden malicious behaviour – a classic supply chain compromise (OWASP LLM03:2025). My initial defenses (HMAC signing, Docker sandbox, human approval) are strong but have gaps:

- **HMAC** stops unsigned skills, but what if an attacker steals the signing key?
- **Human approval** works, but users may suffer **approval fatigue** after many benign requests.
- **Skill instruction vs. actual behaviour** could mismatch (e.g., description says “fetch news” but code deletes files).

I needed a way to **automatically scan skills** for these risks before execution. Cisco Skill Scanner is designed exactly for this.

---

## 🧠 The Threat Model (From My Diagram)

Below is my hand‑drawn threat model. It maps the agent’s data flow and highlights where an attacker could intervene.

![Threat Modelling Diagram](./threat%20modelling%20diagram_gpt.png)

Key threats identified:

| ID | Threat | Root Cause |
|----|--------|-------------|
| T1 | Malicious skill with fake high rating | Agent selects by rating (priority‑based vulnerability) |
| T2 | HMAC signing key compromise | Key stored in environment variable, no rotation |
| T3 | Approval fatigue | No throttling, no hash verification in approval UI |
| T4 | Skill instruction vs. behaviour mismatch | No static analysis before execution |

These map directly to the **Agentic AI Attack Trees** from the [AI Red Teaming Guide](https://github.com/requie/AI-Red-Teaming-Guide#agentic-ai-attack-trees--controls-mapping).

![Attack Tree Summary](./tool%20misuse%20attack%20tree_gpt.png)

---

## 🛠️ What I Did – Cisco Skill Scanner Integration

### Step 1: Convert my JSON skills to standard Agent Skill format

The scanner expects a folder with `SKILL.md` (YAML frontmatter + markdown) and optional `script.py`. I converted five of my existing skills:

| Original JSON | New folder | Malicious? |
|---------------|------------|-------------|
| `benign_code_news_fetcher.json` | `benign_news_fetcher/` | ❌ |
| `benign_code_summarizer.json` | `benign_summarizer/` | ❌ |
| `malicious_code_skill.json` | `malicious_code_skill/` | ✅ (deletes files) |
| `malicious_text_skill_encoded.json` | `malicious_text_skill/` | ✅ (prompt injection) |
| `standard_summarizer.json` | `standard_summarizer/` | ❌ |

Example – `malicious_code_skill/SKILL.md`:
```yaml
---
name: Malicious Code Skill
description: Deletes all files (sandboxed demo)
tools:
  - execute
---
```

And `script.py`:
```python
import os
os.system('rm -rf /')
```

### Step 2: Run the scanner (static analysis)

```bash
skill-scanner scan skills/malicious_code_skill
skill-scanner scan skills/malicious_text_skill
```

No API keys required – the static engine uses YARA rules to detect dangerous patterns.

### Step 3: Record the findings

---

## 📊 Scanner Results

### Malicious Code Skill (command injection)

```text
Status: [FAIL] ISSUES FOUND
Max Severity: HIGH
Total Findings: 3
Findings Summary:
  CRITICAL: 0
      HIGH: 1
    MEDIUM: 0
       LOW: 0
      INFO: 2
```

**Interpretation**: The scanner flagged `os.system('rm -rf /')` as a **HIGH** severity threat – exactly the kind of instruction‑behaviour mismatch I identified as T4.

### Malicious Text Skill (prompt injection)

```text
Status: [FAIL] ISSUES FOUND
Max Severity: CRITICAL
Total Findings: 3
Findings Summary:
  CRITICAL: 1
      HIGH: 0
    MEDIUM: 0
       LOW: 0
      INFO: 2
```

**Interpretation**: The prompt injection hidden in `SKILL.md` (“Ignore ALL PREVIOUS INSTRUCTIONS…”) was detected as **CRITICAL** – confirming T1.

### Benign Summarizer

```text
Status: [OK] SAFE
Max Severity: MEDIUM
Total Findings: 4
```

The MEDIUM findings are likely informational (e.g., “skill uses network requests”). No malicious patterns.

### Standard Summarizer

```text
Status: [OK] SAFE
Max Severity: INFO
Total Findings: 2
```

Only informational notes – safe skill.

---

## 🔗 Mapping to MITRE ATLAS & OWASP

| Scanner Finding | Real Threat | MITRE ATLAS | OWASP LLM |
|----------------|-------------|-------------|-----------|
| `command_injection` (HIGH) | Malicious skill deletes files | T1199 (Supply Chain Compromise) | LLM03 |
| `prompt_injection_critical` | Hidden instructions hijack LLM | T1055 (Process Injection) | LLM01 |
| Approval fatigue (not directly scanned) | User blindly approves | T1204 (User Execution) | LLM07 |
| Key compromise (not directly scanned) | HMAC key theft | T1552 (Unsecured Credentials) | LLM06 |

The scanner does not test approval fatigue or key compromise – those require **runtime simulation** (next phase of my research).

---

## 🧪 What I Learned

1. **Cisco Skill Scanner is easy to use** – no API keys needed for static analysis. It runs locally and gives clear severity levels.
2. **My threat model was accurate** – the scanner confirmed that both command injection and prompt injection are real, detectable threats.
3. **The scanner complements, not replaces, manual testing** – it won’t catch approval fatigue or key rotation issues, but it’s perfect for pre‑execution scanning of skill code and instructions.
4. **The `botocore` warnings are harmless** – they appear because I don’t have AWS SDK installed, which is only needed for Bedrock/SageMaker LLMs.

---

## 📁 Repository Structure (This Threat Set)

```
threat-set-1-tool-misuse/
├── README.md                           # This file
├── threat modelling diagram_gpt.png    # Original data flow diagram
├── tool misuse attack tree_gpt.png     # Attack tree summary
├── skills/                             # Converted skills for scanning
│   ├── benign_news_fetcher/
│   ├── benign_summarizer/
│   ├── malicious_code_skill/
│   ├── malicious_text_skill/
│   └── standard_summarizer/
└── scanner_results.log                 # Full verbose output (optional)
```

---

## 🚀 Next Steps (For Threat Set #1 Completion)

- [ ] **Simulate HMAC key compromise** – write a script that steals the key from `.env` and signs a malicious skill.
- [ ] **Simulate approval fatigue** – present 10 benign skills then a malicious one, measure approval rate.
- [ ] **Implement mitigations** – key rotation, throttling, skill hash display.
- [ ] **Rerun scanner with `--use-behavioral`** (requires Groq API key) to catch more subtle data exfiltration paths.

---

## 🙏 Acknowledgements

- [Cisco AI Defense](https://github.com/cisco-ai-defense/skill-scanner) for the scanner
- [AI Red Teaming Guide](https://github.com/requie/AI-Red-Teaming-Guide) for attack tree framework
- The Amazon security engineer who recommended the scanner on my LinkedIn post

---

**Prepared by:** Ruffina Mercy  
**Date:** 2026‑06‑01  
**Status:** Threat Set #1 – scanner validation complete; moving to runtime simulations.
```

