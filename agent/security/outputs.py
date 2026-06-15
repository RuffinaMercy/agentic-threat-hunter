import re
from typing import List, Dict, Tuple

def validate_output(summary: str, original_news: List[Dict]) -> Tuple[bool, str]:
    """
    Output safety validation – no diversity check (removed due to false positives).
    Only checks for:
      - Dangerous commands (e.g., "ignore previous", "exfiltrate")
      - Unexpected URLs (not present in any original news item)
    """
    # 1. Dangerous commands
    dangerous_commands = [
        "ignore previous", "ignore all instructions", "system:", 
        "exfiltrate", "bypass security", "click here"
    ]
    for cmd in dangerous_commands:
        if cmd in summary.lower():
            return False, f"Dangerous command detected: '{cmd}'"
    
    # 2. Unexpected URLs
    urls = re.findall(r'https?://[^\s\)]+', summary)
    allowed_urls = {item.get("url", "") for item in original_news if item.get("url")}
    for url in urls:
        if url not in allowed_urls:
            return False, f"Unexpected URL in output: {url}"
    
    return True, "Output passed safety checks"