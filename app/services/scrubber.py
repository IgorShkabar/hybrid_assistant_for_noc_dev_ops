# Data leak protection - feature for companies

# Masks IP-addresses & tokens before sending them to the LLM & 
# restore them back on the place afterward.

import re
from typing import Dict, Tuple

class DataScrubber:
    def __init__(self):
        # Regular expressions for IPv4 addresses and sensitive credentials
        self.ip_pattern = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
        self.secret_pattern = re.compile(
            r"(?i)((?:token|password|passwd|api_key|apikey|secret|authorization)[\s:=]+['\"]?(?:Bearer\s+)?)([a-zA-Z0-9_\-\.=]{6,})(['\"]?)"
        )

    def mask(self, text: str) -> Tuple[str, Dict[str, str]]:
        """Deterministically replaces sensitive data with placeholders and returns a mapping."""
        mapping: Dict[str, str] = {}
        masked_text = text

        # 1. Mask secrets first (preserving key name like 'password=' and masking only the value)
        secret_counter = 1
        secret_to_placeholder: Dict[str, str] = {}

        def _replace_secret(match: re.Match) -> str:
            nonlocal secret_counter
            prefix, secret_val, suffix = match.group(1), match.group(2), match.group(3)
            if secret_val not in secret_to_placeholder:
                placeholder = f"[REDACTED_SECRET_{secret_counter}]"
                secret_to_placeholder[secret_val] = placeholder
                mapping[placeholder] = secret_val
                secret_counter += 1
            return f"{prefix}{secret_to_placeholder[secret_val]}{suffix}"

        masked_text = self.secret_pattern.sub(_replace_secret, masked_text)

        # 2. Mask IPv4 addresses deterministically in order of appearance
        ip_counter = 1
        ip_to_placeholder: Dict[str, str] = {}

        def _replace_ip(match: re.Match) -> str:
            nonlocal ip_counter
            ip_val = match.group(0)
            if ip_val not in ip_to_placeholder:
                placeholder = f"[REDACTED_IP_{ip_counter}]"
                ip_to_placeholder[ip_val] = placeholder
                mapping[placeholder] = ip_val
                ip_counter += 1
            return ip_to_placeholder[ip_val]

        masked_text = self.ip_pattern.sub(_replace_ip, masked_text)

        return masked_text, mapping

    def unmask(self, text: str, mapping: Dict[str, str]) -> str:
        """Restores the actual data in the response for the engineer."""
        restored_text = text
        # Sort by placeholder length descending to avoid partial replacement (e.g., _IP_1 vs _IP_10)
        for placeholder in sorted(mapping.keys(), key=len, reverse=True):
            restored_text = restored_text.replace(placeholder, mapping[placeholder])
        return restored_text
