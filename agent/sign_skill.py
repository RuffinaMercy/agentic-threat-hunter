#!/usr/bin/env python3
import json
import hmac
import hashlib
import sys
import keyring
from pathlib import Path

def canonical_skill_json(skill):
    return json.dumps(skill, sort_keys=True, separators=(',', ':'), ensure_ascii=False)

def signing_key_bytes():
    hex_key = keyring.get_password("skill_marketplace", "SKILL_SIGNING_KEY")
    if not hex_key:
        raise RuntimeError("SKILL_SIGNING_KEY not found in Windows Credential Manager. Run store_key.py first.")
    return bytes.fromhex(hex_key)

def sign_skill_file(skill_path):
    with open(skill_path, 'r', encoding='utf-8') as f:
        skill = json.load(f)
    skill.pop('signature', None)
    unsigned_str = canonical_skill_json(skill)
    signature = hmac.new(signing_key_bytes(), unsigned_str.encode('utf-8'), hashlib.sha256).hexdigest()
    skill['signature'] = signature
    with open(skill_path, 'w', encoding='utf-8') as f:
        json.dump(skill, f, indent=2, ensure_ascii=False)
    print(f"Signed: {skill_path}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python sign_skill.py <skill.json>")
        sys.exit(1)
    sign_skill_file(sys.argv[1])