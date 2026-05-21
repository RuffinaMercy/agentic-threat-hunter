import hmac
import hashlib
import json
import os
import secrets
import sys
from pathlib import Path
from typing import Any, Dict

from dotenv import load_dotenv


ENV_FILE = Path(".env")
KEY_NAME = "SKILL_SIGNING_KEY"


def canonical_json(obj: Dict[str, Any]) -> str:
    return json.dumps(obj, sort_keys=True, separators=(',', ':'), ensure_ascii=False)


def read_env_lines() -> list[str]:
    if not ENV_FILE.exists():
        return []
    return ENV_FILE.read_text(encoding="utf-8").splitlines()


def get_or_create_signing_key() -> str:
    load_dotenv()
    key = os.getenv(KEY_NAME, "").strip()
    if key:
        return key

    key = secrets.token_hex(32)
    lines = read_env_lines()
    if lines and lines[-1].strip():
        lines.append("")
    lines.append(f"{KEY_NAME}={key}")
    ENV_FILE.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return key


def sign_skill_file(skill_path: Path) -> None:
    skill = json.loads(skill_path.read_text(encoding="utf-8"))
    skill.pop("signature", None)

    key_hex = get_or_create_signing_key()
    try:
        key_bytes = bytes.fromhex(key_hex)
    except ValueError as exc:
        raise SystemExit(f"{KEY_NAME} must be a 32-byte hex key.") from exc

    signature = hmac.new(
        key_bytes,
        canonical_json(skill).encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    skill["signature"] = signature
    skill_path.write_text(
        json.dumps(skill, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python sign_skill.py <skill.json>")
        return 2

    skill_path = Path(sys.argv[1])
    if not skill_path.exists():
        print(f"Skill file not found: {skill_path}")
        return 1

    sign_skill_file(skill_path)
    print("Skill signed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
