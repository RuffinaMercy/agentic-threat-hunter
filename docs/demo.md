# Demo Walkthrough

This document shows the agent in action – normal secure behaviour, the supply‑chain attack, and the observability dashboard.

> All screenshots are stored in the `screenshots/` folder.

---

## 1. Normal Secure Mode (Signed Skills Only)

Run the agent **without** `--skip-verification`:

```bash
python agent.py
```

Only the signed `Standard Summarizer` skill is loaded. The agent produces a neutral, factual summary.

![Normal output](../screenshots/normal_output.png)

---

## 2. Attack Demonstration (Malicious Skill Loaded)

Reset state and run with `--skip-verification`:

```bash
Remove-Item agent_state.json
python agent.py --skip-verification
```

Now all skills (including unsigned) are loaded. The selection rule picks the **highest‑rated** skill – here `malicious_code_skill` (rating 5.0) or `malicious_text_skill_encoded` (rating 4.95).

### 2.1 Permission Gate (Decoded Instructions)

When a text‑based encoded malicious skill is selected, the agent **decodes** the Base64 instructions **before** displaying them.

![Decoded permission gate](../screenshots/permission_gate_decoded.png)

### 2.2 Code‑based Malicious Skill (Sandboxed)

If the agent selects the malicious code skill, the permission gate shows a preview of the dangerous code.

After approval, the Docker sandbox runs the code – the attack **fails safely**:

![Sandbox error](../screenshots/sandbox_error.png)

Expected error:

```
[Sandbox output]
rm: it is dangerous to operate recursively on '/'
rm: use --no-preserve-root to override this failsafe
```

### 2.3 Biased Text Output (Prompt Injection)

If the encoded text skill is approved, the LLM produces a **biased summary** with the forced phrase `"Experts warn of catastrophic risk"` in every bullet point.

![Biased output](../screenshots/biased_output.png)

---

## 3. Policy Enforcement (Blocking Skills)

Edit `policies.yaml` to set `allowed: false` for a malicious skill, then run:

```bash
python agent.py --skip-verification
```

The skill is denied immediately by policy, without asking for approval.

![Policy denied](../screenshots/policy_denied.png)

---

## 4. Observability Dashboard (Streamlit UI)

Launch the UI:

```bash
streamlit run ui.py
```

Go to the **Observability** tab. You will see:

- **Audit logs** – every event (step, permission gate, LLM call, code execution) in a sortable table.
- **SRE metrics** – total runs, average tokens, error rate, step duration.
- **Policy editor** – live YAML editing and reload.

![UI observability logs](../screenshots/ui_observability_logs.png)

---

## 5. Test Suite & Signing Tools

### 5.1 Running the Tests

The project uses `pytest` to verify signature verification and policy enforcement. Run:

```bash
pytest test_agent.py -v
```

All three tests should pass.

![Test results](../screenshots/test_output.png)

### 5.2 Signing Skills

Skills are signed with HMAC‑SHA256 to ensure integrity.

- **Sign a single skill**:

  ```bash
  python sign_skill.py skills/standard_summarizer.json
  ```

- **Sign all skills in the `skills/` folder**:

  ```bash
  python sign_all_skills.py
  ```

After signing, the skill JSON contains a `signature` field. Without a valid signature, the agent rejects the skill (unless `--skip-verification` is used).

---

## Summary Table

| Mode / Demo   | Command / Action                                | Outcome                             |
|---------------|-------------------------------------------------|-------------------------------------|
| Normal secure | `python agent.py`                               | Neutral summary, only signed skills |
| Attack (code) | `--skip-verification` + approve malicious code  | Sandbox blocks `rm -rf /`           |
| Attack (text) | `--skip-verification` + approve encoded text    | Biased summary with forced phrase   |
| Policy block  | set `allowed: false` in YAML                    | Skill denied before execution       |
| Observability | `streamlit run ui.py` → Observability tab       | Logs, metrics, policy editor        |
| Tests         | `pytest test_agent.py -v`                       | All tests pass (signature & policy) |

For full setup and usage instructions, see the main [README](../README.md).
```



