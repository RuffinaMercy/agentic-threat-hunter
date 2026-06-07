
import keyring
from pathlib import Path
from sign_skill import sign_skill_file

SERVICE_NAME = "skill_marketplace"
KEY_NAME = "SKILL_SIGNING_KEY"
# Skills directory is one level above the agent folder
SKILLS_DIR = Path(__file__).resolve().parent.parent / "skills"

def main():
    if not SKILLS_DIR.exists():
        print(f"❌ Skills directory not found: {SKILLS_DIR}")
        return

    # Verify key exists before attempting to sign
    if not keyring.get_password(SERVICE_NAME, KEY_NAME):
        print("❌ No signing key found in Windows Credential Manager.")
        print("   Run 'python store_key.py' first to generate and store a key.")
        return

    skill_files = list(SKILLS_DIR.glob("*.json"))
    if not skill_files:
        print(f"⚠️  No JSON skill files found in {SKILLS_DIR}")
        return

    print(f"Found {len(skill_files)} skill(s) to sign.\n")
    success_count = 0
    for skill_path in skill_files:
        try:
            sign_skill_file(str(skill_path))
            success_count += 1
        except Exception as e:
            print(f"❌ Failed to sign {skill_path.name}: {e}")

    print(f"\n✅ Signed {success_count} of {len(skill_files)} skill(s).")

if __name__ == "__main__":
    main()