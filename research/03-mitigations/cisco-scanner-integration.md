# Integrating Cisco Skill Scanner for Pre‑Execution Blocking

## Why We Added This
Even with HMAC signing, a compromised key would allow any signed skill to run. We needed a **second, independent check** that looks at the skill’s actual content.

## How It Works in Our Agent
1. In `load_skills()`, before HMAC verification, we call `scan_skill_with_cisco(skill)`.
2. The function:
   - Converts the JSON skill into a temporary directory with `SKILL.md` and `script.py`.
   - Runs `skill-scanner scan` (static + optional behavioral).
   - Parses the output for `CRITICAL:` and `HIGH:` counts.
   - Returns `False` (block) if either count > 0.
3. If blocked, the skill is skipped entirely; otherwise, HMAC verification proceeds.

## Example Scanner Outputs
- `malicious_code_skill.json` → **HIGH** (command injection) → blocked.
- `malicious_text_skill_encoded.json` → **CRITICAL** (prompt injection) → blocked.
- Benign skills → no CRITICAL/HIGH → allowed.

## Why This Is Effective
- It catches threats **even if the HMAC key is stolen**.
- It uses Cisco’s YARA rules (continuously updated).
- It fails open if the scanner is missing (agent still works, but with reduced security).

## Code Snippet
```python
# Inside load_skills()
if not skip_verification:
    is_safe, msg = scan_skill_with_cisco(skill)
    if not is_safe:
        log(f"Skill {path.name} BLOCKED: {msg}")
        continue