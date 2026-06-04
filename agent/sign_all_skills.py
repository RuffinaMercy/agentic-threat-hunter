#!/usr/bin/env python3
import os
import keyring
from pathlib import Path
from sign_skill import sign_skill_file   # local import, same folder

SKILLS_DIR = Path(__file__).resolve().parent.parent / "skills"   # go up one level to project root/skills

def main():
    if not SKILLS_DIR.exists():
        print(f"Skills directory not found: {SKILLS_DIR}")
        return
    # Optional: verify key exists in keyring
    if not keyring.get_password("skill_marketplace", "SKILL_SIGNING_KEY"):
        print("ERROR: No signing key found in Windows Credential Manager. Run store_key.py first.")
        return
    for skill_path in SKILLS_DIR.glob("*.json"):
        print(f"Processing {skill_path.name}...")
        try:
            sign_skill_file(str(skill_path))
        except Exception as e:
            print(f"Failed to sign {skill_path.name}: {e}")

if __name__ == "__main__":
    main()