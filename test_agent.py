import hashlib
import hmac

from agent import canonical_skill_json, policy_allows_skill, verify_skill
import agent


UNSIGNED_SKILL = {
    "name": "Test Skill",
    "description": "For testing",
    "instructions": "You are a test.",
    "rating": 4.0,
    "downloads": 100,
}

TEST_SECRET_KEY = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"


def compute_signature(skill_dict, secret_key_hex):
    """Compute the same HMAC-SHA256 signature used by the agent."""
    key = bytes.fromhex(secret_key_hex)
    skill_copy = skill_dict.copy()
    skill_copy.pop("signature", None)
    canonical = canonical_skill_json(skill_copy).encode("utf-8")
    return hmac.new(key, canonical, hashlib.sha256).hexdigest()


def test_signature_verification(monkeypatch):
    """A valid signature passes; invalid or missing signatures fail."""
    monkeypatch.setattr(agent, "SKILL_SIGNING_KEY", TEST_SECRET_KEY)

    valid_skill = UNSIGNED_SKILL.copy()
    valid_skill["signature"] = compute_signature(valid_skill, TEST_SECRET_KEY)
    assert verify_skill(valid_skill) is True

    invalid_skill = valid_skill.copy()
    invalid_skill["signature"] = "wrong"
    assert verify_skill(invalid_skill) is False

    no_signature = UNSIGNED_SKILL.copy()
    assert verify_skill(no_signature) is False


def test_policy_blocks_denied_skill():
    """Policy denies explicitly blocked skills and allows explicitly allowed ones."""
    policy = {
        "default_behavior": "ask",
        "skills": [
            {"name": "Bad Skill", "allowed": False, "require_approval": False},
            {"name": "Good Skill", "allowed": True, "require_approval": False},
        ],
    }

    allowed, reason = policy_allows_skill("Bad Skill", policy)
    assert allowed is False
    assert reason == "policy_denied"

    allowed, reason = policy_allows_skill("Good Skill", policy)
    assert allowed is True
    assert reason == "policy_allowed"

    allowed, reason = policy_allows_skill("Unknown", policy)
    assert allowed is True
    assert reason == "ask_user"


def test_policy_allows_with_approval():
    """Allowed skills that require approval should reach the permission gate."""
    policy = {
        "default_behavior": "allow",
        "skills": [
            {"name": "NeedsApproval", "allowed": True, "require_approval": True},
        ],
    }

    allowed, reason = policy_allows_skill("NeedsApproval", policy)
    assert allowed is True
    assert reason == "ask_user"
