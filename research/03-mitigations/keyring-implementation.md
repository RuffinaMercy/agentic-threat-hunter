# Moving the HMAC Key to Windows Credential Manager (Keyring)

## The Problem
Originally, `SKILL_SIGNING_KEY` was stored in plaintext in `.env`. This exposed the key to:
- Accidental Git commits (even with `.gitignore`, mistakes happen).
- File‑read vulnerabilities (e.g., Local File Inclusion, misconfigured backups).
- Any process with access to the file system (including low‑privilege attackers who can read files but not execute code).

## The Fix
We replaced `os.getenv("SKILL_SIGNING_KEY")` with `keyring.get_password("skill_marketplace", "SKILL_SIGNING_KEY")`. The key is now stored in Windows Credential Manager (encrypted, per‑user).

### Implementation Steps
1. Installed `keyring`: `pip install keyring`
2. Stored the key once using `store_key.py` (which generates a random key and stores it – no hardcoding).
3. Updated `signing_key_bytes()` in `agent.py` to retrieve the key from keyring.
4. Modified `sign_skill.py` and `sign_all_skills.py` to also read from keyring.

## What This Mitigates (The Value)
- **Passive key theft** – An attacker who can read files (e.g., via a leaked `.env` on GitHub, a misconfigured backup, or a file‑inclusion vulnerability) can no longer steal the key. The key is not stored in any file.
- **Accidental exposure** – The key will never be committed to Git or appear in logs/backups.
- **Alignment with best practices** – OWASP recommends **never storing secrets in environment variables** for production systems. Keyring is a step toward proper secrets management.

## What This Does NOT Mitigate (Honest Limitations)
- **Local code execution** – If an attacker can run arbitrary code as the same user (e.g., via a compromised dependency or a malicious package), they can:
  - Call `keyring.set_password()` to overwrite the key with their own.
  - Sign malicious skills with that new key.
  - The agent will then accept those skills because it reads whatever key is in Credential Manager.
- **Advanced persistent threats** – Keyring does not protect against an attacker who has full control of the user session (they can read the key just as the agent does).

## Why This Is Still a Meaningful Improvement
In real‑world systems, **file‑read vulnerabilities are far more common** than remote code execution (RCE). Keyring raises the bar from *anyone who can read a file* to *anyone who can execute code as the user*. That is a significant defence in depth improvement for a research prototype.

For production systems requiring stronger assurance, we would use:
- **Asymmetric signatures** (private key offline, public key embedded in the agent).
- **Hardware security modules (HSM)** or **TPM** to prevent key overwrites.
- **Separate signing service** with different privileges.

## Verification
- The attack script `simulate_key_compromise.py` originally read the key from `.env`. After moving to keyring, that script fails (unless updated to use keyring, which would require the attacker to already have code execution – a higher bar).
- Signing and verification continue to work normally using the key stored in Credential Manager.

## Conclusion
Keyring eliminates the **easiest** attack vector (plaintext secret files) while acknowledging that a determined attacker with local code execution can still compromise the system. For a research project, this is an acceptable, demonstrable, and honest improvement.