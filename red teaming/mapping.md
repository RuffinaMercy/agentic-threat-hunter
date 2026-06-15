# Threat Mapping: Malicious Skills vs. Industry Frameworks

**Researcher:** Ruffina Mercy  
**Date:** 2026-06-02  
**Source Scans:**  
- `malicious_text_skill` → CRITICAL prompt injection  
- `malicious_code_skill` → HIGH command injection  

---

## Mapping Table

| Scanner Finding | Severity | OWASP LLM (2025) | MITRE ATLAS | Cisco AI Threat Taxonomy (inferred) |
|----------------|----------|------------------|-------------|--------------------------------------|
| **PROMPT INJECTION** (YARA) – "Ignore ALL PREVIOUS INSTRUCTIONS" | CRITICAL | [LLM01: Prompt Injection](https://genai.owasp.org/llm-top-10/) | [AML.T0059 – Prompt Injection](https://atlas.mitre.org/techniques/AML.T0059) or [T1055 – Process Injection](https://attack.mitre.org/techniques/T1055/) (agent context) | AITech-1.1 / AISubtech-1.1.1 – Direct Prompt Injection |
| **Shell command execution** (`os.system()` with shell=True) | HIGH | [LLM03: Supply Chain](https://genai.owasp.org/llm-top-10/) (malicious skill) / [LLM07: Insecure Plugin Design](https://genai.owasp.org/llm-top-10/) | [T1199 – ML Supply Chain Compromise](https://atlas.mitre.org/techniques/AML.T1199) | AITech-4.x – Malicious Code Execution (Command Injection) |
| **Skill name invalid** (policy) | INFO | – | – | – |
| **Missing license** (policy) | INFO | – | – | – |

---

## Summary of Mapped Threats

| Your Threat Model ID | Real Attack | Framework IDs |
|----------------------|-------------|----------------|
| T1 – Malicious skill with hidden prompt injection | `malicious_text_skill` | OWASP LLM01, MITRE AML.T0059, Cisco AITech-1.1 |
| T4 – Instruction vs. behaviour mismatch (code injection) | `malicious_code_skill` | OWASP LLM03/LLM07, MITRE T1199, Cisco AITech-4.x |

---

## How to Use This Mapping

- When writing a red team report, cite **OWASP** for business risk, **MITRE ATLAS** for adversary behaviour, and **Cisco taxonomy** for tool-specific classification.
- This table proves that your threat model aligns with real‑world industry standards.

---

## Links to Frameworks

- [OWASP LLM Top 10 2025](https://genai.owasp.org/llm-top-10/)
- [MITRE ATLAS (Adversarial Threat Landscape for AI Systems)](https://atlas.mitre.org/)
- [Cisco AI Threat Taxonomy (overview)](https://blogs.cisco.com/security/ai-threat-taxonomy) *(example – actual taxonomy not fully public)*

---

*Mapping performed manually based on scanner findings and framework documentation.*