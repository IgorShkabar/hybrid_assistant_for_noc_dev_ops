# Data leak protection - feature for companies

# Masks IP-addresses & tokens before sending them to the LLM & 
# restore them back on the place afterward.

import re
from typing import Dict, Tuple

class DataScrubber():
    def __init__(self):
        # Regular expressions for the search IPv4 & typical keys/passwords
        self.patterns = {
            "IP": r"\b(?:\d{1,3}\.){3}\d{1,3}\b",
            "SECRET": r"(?i)(?:token|password|api_key|secret)[\s:=]+['\"]?([a-zA-Z0-9_\-\.]{6,})['\"]?",
        }

    def mask(self, Text: str) -> Tuple[str, Dict[str, str]]:
        """Replaces sensitive data with placeholders and returns a map of the replacements."""
        mapping: Dict[str, str] = {}
        masked_text = Text

        # I am masking IP-addresses
        ips = set(re.findall(self.patterns["IP"], masked_text))
        for idx, ip in enumerate(ips, start=1):
            placeholder = f"[REDACTED_IP_{idx}]"
            mapping[placeholder] = ip
            masked_text = masked_text.replace(ip, placeholder)

        # I am masking secrets and passwords
        secrets = set(re.findall(self.patterns["SECRET"], masked_text))
        for idx, secret in enumerate(secrets, start=1):
            placeholder = f"[REDACTED_SECRET_{idx}]"
            mapping[placeholder] = secret
            masked_text = masked_text.replace(secret, placeholder)

        return masked_text, mapping

    def unmask(self, text: str, mapping: Dict[str, str]) -> str:
        """Restores the actual data in the responce for the engineer."""
        restored_text = text
        for placeholder, original_value in mapping.items():
            restored_text = restored_text.replace(placeholder, original_value)
        return restored_text
    
            

