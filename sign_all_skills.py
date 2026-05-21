from pathlib import Path

from sign_skill import sign_skill_file


SKILLS_DIR = Path("skills")


def main() -> int:
    if not SKILLS_DIR.exists():
        print("skills/ folder does not exist.")
        return 1

    skill_paths = sorted(SKILLS_DIR.glob("*.json"))
    if not skill_paths:
        print("No skill JSON files found.")
        return 0

    for skill_path in skill_paths:
        sign_skill_file(skill_path)
        print(f"Skill signed: {skill_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
