# Supply Chain Attack Analysis: Tool Misuse in AI Agent Skills

**Researcher:** Ruffina Mercy  
**Date:** 2026‑06‑04  
**Related Files:**  

![Threat Modelling Diagram](../01-threat-modelling/threat-modelling-diagram.png)
![Attack Tree](../01-threat-modelling/attack-tree-tool-misuse.png)

- Attack simulation script: `../02-attack-simulation/simulate_key_compromise.py`
- Keyring mitigation: `../03-mitigations/keyring-implementation.md`
- Cisco scanner mitigation: `../03-mitigations/cisco-scanner-integration.md`
- Malicious code skill report: `./malicious-code-skill-report.md`
- Malicious text skill report: `./malicious-text-skill-report.md`

---

## 1. Executive Summary

This research analyses a **supply chain attack** against my AI news summariser agent. The agent loads third‑party “skills” from a marketplace, selects them by rating, verifies their HMAC signature, and executes them. I identified three critical threats:

1. **Malicious skill with fake high rating** (OWASP LLM03, MITRE T1199)
2. **HMAC signing key compromise** (MITRE T1552)
3. **User approval fatigue** (MITRE T1204)

I simulated a key compromise (stealing the key from `.env` and signing a malicious skill) and then implemented two layered mitigations:
- **Keyring** – moved the signing key to Windows Credential Manager (encrypted, per‑user).
- **Cisco Skill Scanner** – integrated pre‑execution static analysis to block skills with `CRITICAL` or `HIGH` severity findings.

The mitigations were validated by running the scanner on real malicious skills. The agent now blocks prompt injection and command injection before HMAC verification, and the signing key is no longer exposed in plaintext.

---

## 2. Threat Model Overview

### 2.1 Data Flow Diagram

![Threat Modelling Diagram](../01-threat-modelling/threat-modelling-diagram.png)

The diagram shows how the agent fetches news, loads skills from a marketplace, and uses an LLM to produce a summary. The skill marketplace is the main entry point for supply chain attacks.

### 2.2 Attack Tree – Tool Misuse

![Attack Tree](../01-threat-modelling/attack-tree-tool-misuse.png)

The attack tree focuses on **Tool Misuse** (based on the AI Red Teaming Guide). The attacker’s path is:
Upload malicious skill with 5 stars
→ Agent selects by rating
→ Skill passes HMAC (or key stolen)
→ User approves
→ Malicious action runs

text

I prioritised two branches: **key compromise** and **malicious content** (prompt/command injection).

---

## 3. Attack Simulation: HMAC Key Compromise

### 3.1 The Vulnerability

Originally, the signing key was read from `.env` (plaintext). Any process on the machine could read it, and it could be accidentally committed to Git.

### 3.2 The Exploit

I wrote `simulate_key_compromise.py` (see `../02-attack-simulation/`). The script:
1. Reads the key from `.env`.
2. Creates a new malicious skill (`malicious_signed.json`) with a high rating.
3. Signs it using the stolen key.
4. Optionally re‑signs all existing skills (stealth mode).

After running the script, the agent accepted the malicious skill and executed it (biased summary or sandboxed command). This proves that a plaintext key is a critical weakness.

---

## 4. Mitigations Implemented

Two independent layers were added **before** the agent’s existing HMAC verification and permission gate.

### 4.1 Mitigation 1: Secure Key Storage with Keyring

- Replaced `os.getenv("SKILL_SIGNING_KEY")` with `keyring.get_password("skill_marketplace", "SKILL_SIGNING_KEY")`.
- The key is now stored in Windows Credential Manager (encrypted, per‑user).
- The attack script can no longer steal the key from `.env` (unless rewritten to use keyring, which requires user‑level access).

**Framework mapping:** MITRE ATLAS T1552 (mitigated), OWASP LLM06 (Sensitive Information Disclosure).

### 4.2 Mitigation 2: Pre‑Execution Scanning with Cisco Skill Scanner

- In `load_skills()`, before HMAC verification, we call `scan_skill_with_cisco(skill)`.
- The function:
  - Converts the JSON skill into a temporary `SKILL.md` + `script.py`.
  - Runs `skill-scanner scan` (static engine).
  - Parses the output for `CRITICAL:` and `HIGH:` severity counts.
  - Blocks the skill if either count > 0.
- The scanner uses YARA rules to detect prompt injection, command injection, etc.

**Framework mapping:** OWASP LLM03 (Supply Chain), MITRE ATLAS T1199 (ML Supply Chain Compromise).

---

## 5. Scanner Validation Results

I ran the scanner on two malicious skills and several benign skills. The results confirm that the scanner blocks real threats.

### 5.1 Malicious Code Skill (Command Injection)

**Report:** `malicious-code-skill-report.md`
Status: [FAIL] ISSUES FOUND
Max Severity: HIGH
Findings: command_injection (os.system call)
→ Blocked by scanner.

text

### 5.2 Malicious Text Skill (Prompt Injection)

**Report:** `malicious-text-skill-report.md`
Status: [FAIL] ISSUES FOUND
Max Severity: CRITICAL
Findings: prompt_injection (YARA rule)
→ Blocked by scanner.

text

### 5.3 Benign Skills (e.g., Standard Summarizer)

- No `CRITICAL` or `HIGH` findings → passed scanner.
- HMAC verification passed → loaded and executed safely.

---

## 6. Mapping to Industry Frameworks

| Threat | OWASP LLM 2025 | MITRE ATLAS | Mitigation |
|--------|----------------|-------------|-------------|
| Malicious skill with fake rating | LLM03: Supply Chain | T1199 (ML Supply Chain Compromise) | Cisco scanner blocks |
| HMAC key stored in `.env` | LLM06: Sensitive Information Disclosure | T1552 (Unsecured Credentials) | Keyring (Credential Manager) |
| User approval fatigue | LLM07: Insecure Plugin Design | T1204 (User Execution) | Human gate (remains, but could be improved) |
| Indirect prompt injection (RSS) | LLM01: Prompt Injection | AML.T0059 | Not yet mitigated (future work) |

---

## 7. Conclusion

This research demonstrates a **complete security loop** for an AI agent supply chain attack:

1. **Threat model** – identified critical risks using MAESTRO layers and attack trees.
2. **Attack simulation** – proved that a plaintext HMAC key leads to full compromise.
3. **Mitigations** – implemented secure key storage (keyring) and pre‑execution scanning (Cisco Skill Scanner).
4. **Validation** – scanner reports confirm that real malicious skills are blocked.

The agent now has **defence in depth**:
- **Layer 1 (pre‑execution)**: Scanner blocks malicious content.
- **Layer 2 (integrity)**: HMAC ensures only signed skills.
- **Layer 3 (secrets)**: Keyring protects the signing key.
- **Layer 4 (human)**: Permission gate for final approval.

---


## 8. Future Scope

While the current mitigations provide strong defence‑in‑depth, the following improvements would further harden the agent:

- **Key rotation** – Automatically generate a new HMAC signing key every 24 hours and re‑sign all skills. This limits the     window of opportunity if a key is ever compromised.
- **Behavioural scanning** – Enable Cisco Skill Scanner’s `--use-behavioral` flag (requires an LLM API key) to catch subtle mismatches between skill descriptions and actual code behaviour.
- **Indirect prompt injection** – Implement input sanitisation and instruction delimiters for all RSS‑fed content, protecting against hidden attacks via news articles.