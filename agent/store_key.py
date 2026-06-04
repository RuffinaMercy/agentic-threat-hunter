import keyring
import os
from dotenv import load_dotenv

load_dotenv()
hex_key = os.getenv("SKILL_SIGNING_KEY")
if hex_key:
    keyring.set_password("skill_marketplace", "SKILL_SIGNING_KEY", "7f3e4a2b9c1d6e8f0a5b4c3d2e1f6a8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f")
    print("Key stored in Windows Credential Manager.")
else:
    print("No SKILL_SIGNING_KEY found in .env")