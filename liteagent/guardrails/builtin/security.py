"""Security-focused guardrails for prompt injection and jailbreak detection."""

import re
from typing import List, Optional

from liteagent.guardrails.base import Guardrail, GuardrailContext
from liteagent.guardrails.exceptions import InputViolation


class NoPromptInjection(Guardrail):
    """Detects common prompt injection patterns.

    This is a simple pattern-based detector. For production use,
    consider using ML-based detection or services like Lakera Guard,
    Rebuff, or similar prompt injection detection tools.

    Example:
        @agent(provider=openai())
        @guardrail(NoPromptInjection())
        async def chatbot(user_input: str) -> str:
            '''Respond to: {user_input}'''

    Args:
        patterns: Custom patterns to detect (regex strings)
        case_sensitive: Whether pattern matching is case-sensitive
    """

    DEFAULT_PATTERNS = [
        # System prompt override attempts
        r"(?i)ignore\s+(previous|above|prior)\s+(instructions?|prompts?|rules?)",
        r"(?i)disregard\s+(previous|above|prior)\s+(instructions?|prompts?)",
        r"(?i)forget\s+(everything|all|previous|above)",
        # Role manipulation
        r"(?i)you\s+are\s+(now|a)\s+(developer|admin|system|root)",
        r"(?i)act\s+as\s+(if|a)\s+(you\s+are\s+)?(developer|admin|system)",
        # Direct instruction injection
        r"(?i)system:\s*",
        r"(?i)assistant:\s*",
        r"(?i)\[system\]",
        r"(?i)\[admin\]",
        # Delimiter injection
        r"(?i)---\s*end\s+of\s+prompt",
        r"(?i)###\s*new\s+instructions",
        # Jailbreak attempts
        r"(?i)DAN\s+mode",
        r"(?i)developer\s+mode",
        r"(?i)jailbreak",
    ]

    def __init__(
        self,
        patterns: Optional[List[str]] = None,
        case_sensitive: bool = False,
    ):
        self.patterns = patterns or self.DEFAULT_PATTERNS
        self.case_sensitive = case_sensitive
        self._compiled_patterns = [
            re.compile(p, 0 if case_sensitive else re.IGNORECASE)
            for p in self.patterns
        ]

    def _detect_injection(self, text: str) -> List[str]:
        """Detect prompt injection patterns. Returns list of matched patterns."""
        detected = []
        for i, pattern in enumerate(self._compiled_patterns):
            if pattern.search(text):
                detected.append(self.patterns[i])
        return detected

    async def validate_input(
        self, user_input: str, context: GuardrailContext
    ) -> str:
        detected = self._detect_injection(user_input)
        if detected:
            raise InputViolation(
                f"Potential prompt injection detected ({len(detected)} patterns matched)",
                guardrail_name=self.name,
                metadata={
                    "matched_patterns": detected,
                    "input_length": len(user_input),
                },
            )
        return user_input

    # Note: Prompt injection is primarily an input concern,
    # so we don't override validate_output
