#!/usr/bin/env python3
"""
Securely generate and store an HMAC signing key in Windows Credential Manager.
Run this ONCE when setting up the project.
The key is never written to disk or committed to Git.
"""

import keyring
import secrets
import sys

SERVICE_NAME = "skill_marketplace"
KEY_NAME = "SKILL_SIGNING_KEY"

def main():
    # Check if key already exists
    existing = keyring.get_password(SERVICE_NAME, KEY_NAME)
    if existing:
        overwrite = input("A key already exists. Overwrite? (y/N): ").strip().lower()
        if overwrite != 'y':
            print("Aborted.")
            return

    # Generate a secure random 256-bit key (32 bytes = 64 hex characters)
    new_key = secrets.token_hex(32)
    keyring.set_password(SERVICE_NAME, KEY_NAME, new_key)
    print("✅ New HMAC key generated and stored securely in Windows Credential Manager.")
    print("\n⚠️  Save this key offline if you need to recover access (optional):")
    print(f"   {new_key}")
    print("\nDo NOT commit this key to Git or share it.")

if __name__ == "__main__":
    main()