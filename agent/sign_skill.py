#!/usr/bin/env python3
"""
Sign a single skill JSON file using HMAC-SHA256.
The signing key is retrieved from Windows Credential Manager (keyring).
"""

import json
import hmac
import hashlib
import sys
import keyring
from pathlib import Path

SERVICE_NAME = "skill_marketplace"
KEY_NAME = "SKILL_SIGNING_KEY"

def canonical_skill_json(skill):
    """Convert skill dict to a deterministic JSON string for signing."""
    return json.dumps(skill, sort_keys=True, separators=(',', ':'), ensure_ascii=False)

def signing_key_bytes():
    """Retrieve the HMAC key from keyring and return as bytes."""
    hex_key = keyring.get_password(SERVICE_NAME, KEY_NAME)
    if not hex_key:
        raise RuntimeError(
            f"No signing key found in Windows Credential Manager.\n"
            f"Run 'python store_key.py' first to generate and store a key."
        )
    try:
        return bytes.fromhex(hex_key)
    except ValueError as exc:
        raise RuntimeError(f"Invalid hex key in credential manager: {exc}")

def sign_skill_file(skill_path):
    """Load a skill JSON, compute HMAC signature, and write back."""
    skill_path = Path(skill_path)
    if not skill_path.exists():
        raise FileNotFoundError(f"Skill file not found: {skill_path}")

    with open(skill_path, 'r', encoding='utf-8') as f:
        skill = json.load(f)

    # Remove existing signature if present
    skill.pop('signature', None)

    # Compute signature
    unsigned_str = canonical_skill_json(skill)
    signature = hmac.new(
        signing_key_bytes(),
        unsigned_str.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()

    skill['signature'] = signature

    # Write back with pretty formatting
    with open(skill_path, 'w', encoding='utf-8') as f:
        json.dump(skill, f, indent=2, ensure_ascii=False)

    print(f"✅ Signed: {skill_path.name}")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python sign_skill.py <skill.json>")
        sys.exit(1)
    try:
        sign_skill_file(sys.argv[1])
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)