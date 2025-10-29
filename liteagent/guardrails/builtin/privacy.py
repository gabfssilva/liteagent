"""Privacy-focused guardrails for PII and secrets detection."""

import re
from typing import List, Optional

from liteagent.guardrails.base import Guardrail, GuardrailContext
from liteagent.guardrails.exceptions import InputViolation, OutputViolation


class NoPII(Guardrail):
    """Detects and redacts Personally Identifiable Information (PII).

    This implementation uses regex patterns for common PII types.
    For production, consider using dedicated PII detection libraries
    like Microsoft Presidio or cloud services.

    Example:
        @agent(provider=openai())
        @guardrail(NoPII(block_on_detection=False))  # Redacts PII
        async def support_bot(user_input: str) -> str:
            '''Respond to: {user_input}'''

    Args:
        entities: List of PII entity types to detect
                 Options: "email", "phone", "ssn", "credit_card"
        block_on_detection: If True, raises violation; if False, redacts
        redaction_text: Text to replace PII with
    """

    # Regex patterns for common PII types
    PATTERNS = {
        "email": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
        "phone": r"\b(?:\+?1[-.]?)?\(?([0-9]{3})\)?[-.]?([0-9]{3})[-.]?([0-9]{4})\b",
        "ssn": r"\b\d{3}-\d{2}-\d{4}\b",
        "credit_card": r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b",
    }

    def __init__(
        self,
        entities: Optional[List[str]] = None,
        block_on_detection: bool = True,
        redaction_text: str = "[PII_REDACTED]",
    ):
        self.entities = entities or ["email", "phone", "ssn", "credit_card"]
        self.block_on_detection = block_on_detection
        self.redaction_text = redaction_text

        # Validate entity types
        invalid = set(self.entities) - set(self.PATTERNS.keys())
        if invalid:
            raise ValueError(
                f"Unknown PII entity types: {invalid}. "
                f"Valid options: {list(self.PATTERNS.keys())}"
            )

    def _detect_pii(self, text: str) -> dict[str, List[str]]:
        """Detect PII entities in text. Returns dict of entity_type -> matches."""
        detected = {}
        for entity in self.entities:
            pattern = self.PATTERNS[entity]
            matches = re.findall(pattern, text)
            if matches:
                # For phone numbers, matches are tuples - join them
                if entity == "phone" and matches:
                    matches = [
                        "".join(m) if isinstance(m, tuple) else m for m in matches
                    ]
                detected[entity] = matches
        return detected

    def _redact_pii(self, text: str) -> str:
        """Replace PII with redaction text."""
        result = text
        for entity in self.entities:
            pattern = self.PATTERNS[entity]
            result = re.sub(pattern, self.redaction_text, result)
        return result

    async def validate_input(
        self, user_input: str, context: GuardrailContext
    ) -> str:
        detected = self._detect_pii(user_input)
        if detected:
            if self.block_on_detection:
                entity_summary = ", ".join(
                    f"{entity}: {len(matches)}" for entity, matches in detected.items()
                )
                raise InputViolation(
                    f"PII detected in input: {entity_summary}",
                    guardrail_name=self.name,
                    metadata={"detected_pii": detected},
                )
            else:
                return self._redact_pii(user_input)
        return user_input

    async def validate_output(
        self, llm_output: str, context: GuardrailContext
    ) -> str:
        detected = self._detect_pii(llm_output)
        if detected:
            if self.block_on_detection:
                entity_summary = ", ".join(
                    f"{entity}: {len(matches)}" for entity, matches in detected.items()
                )
                raise OutputViolation(
                    f"PII detected in output: {entity_summary}",
                    guardrail_name=self.name,
                    metadata={"detected_pii": detected},
                )
            else:
                return self._redact_pii(llm_output)
        return llm_output


class NoSecrets(Guardrail):
    """Detects and blocks common secret patterns (API keys, tokens, passwords).

    Example:
        @agent(provider=openai())
        @guardrail(NoSecrets())
        async def code_helper(user_input: str) -> str:
            '''Help with: {user_input}'''

    Args:
        secret_patterns: Custom regex patterns to detect secrets
        block_on_detection: If True, raises violation; if False, redacts
    """

    DEFAULT_PATTERNS = {
        "api_key": r"(?i)(api[_-]?key|apikey)\s*[:=]\s*['\"]?([a-zA-Z0-9_\-]{20,})['\"]?",
        "bearer_token": r"(?i)bearer\s+([a-zA-Z0-9_\-\.]{20,})",
        "aws_key": r"(?i)(AKIA[0-9A-Z]{16})",
        "github_token": r"(?i)(ghp_[a-zA-Z0-9]{36})",
        "openai_key": r"(?i)(sk-[a-zA-Z0-9]{20,})",  # Changed to 20+ chars instead of exactly 48
        "password": r"(?i)(password|passwd|pwd)\s*[:=]\s*['\"]?([^\s'\"]{8,})['\"]?",
    }

    def __init__(
        self,
        secret_patterns: Optional[dict] = None,
        block_on_detection: bool = True,
        redaction_text: str = "[SECRET_REDACTED]",
    ):
        self.patterns = secret_patterns or self.DEFAULT_PATTERNS
        self.block_on_detection = block_on_detection
        self.redaction_text = redaction_text

    def _detect_secrets(self, text: str) -> dict[str, List[str]]:
        """Detect secrets in text. Returns dict of secret_type -> matches."""
        detected = {}
        for secret_type, pattern in self.patterns.items():
            matches = re.findall(pattern, text)
            if matches:
                # Extract the actual secret value (often in capture groups)
                if isinstance(matches[0], tuple):
                    matches = [m[-1] for m in matches]  # Last group is usually the value
                detected[secret_type] = matches
        return detected

    def _redact_secrets(self, text: str) -> str:
        """Replace secrets with redaction text."""
        result = text
        for pattern in self.patterns.values():
            result = re.sub(pattern, self.redaction_text, result)
        return result

    async def validate_input(
        self, user_input: str, context: GuardrailContext
    ) -> str:
        detected = self._detect_secrets(user_input)
        if detected:
            secret_types = list(detected.keys())
            if self.block_on_detection:
                raise InputViolation(
                    f"Secrets detected in input: {', '.join(secret_types)}",
                    guardrail_name=self.name,
                    metadata={"detected_secret_types": secret_types},
                )
            else:
                return self._redact_secrets(user_input)
        return user_input

    async def validate_output(
        self, llm_output: str, context: GuardrailContext
    ) -> str:
        detected = self._detect_secrets(llm_output)
        if detected:
            secret_types = list(detected.keys())
            if self.block_on_detection:
                raise OutputViolation(
                    f"Secrets detected in output: {', '.join(secret_types)}",
                    guardrail_name=self.name,
                    metadata={"detected_secret_types": secret_types},
                )
            else:
                return self._redact_secrets(llm_output)
        return llm_output
