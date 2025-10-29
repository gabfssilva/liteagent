"""Content-related guardrails for topic and toxicity control."""

import re
from typing import List

from liteagent.guardrails.base import Guardrail, GuardrailContext
from liteagent.guardrails.exceptions import InputViolation, OutputViolation


class AllowedTopics(Guardrail):
    """Restricts conversations to specific allowed topics.

    This guardrail checks if the input contains keywords related to
    allowed topics. If not, it raises an InputViolation.

    Example:
        @agent(provider=openai())
        @guardrail(AllowedTopics(["weather", "climate", "forecast"]))
        async def weather_bot(user_input: str) -> str:
            '''Respond to: {user_input}'''

    Args:
        topics: List of allowed topic keywords (case-insensitive)
        case_sensitive: Whether to match topics case-sensitively
        validate_output: Whether to also validate output contains allowed topics
    """

    def __init__(
        self,
        topics: List[str],
        case_sensitive: bool = False,
        validate_output: bool = False,
    ):
        self.topics = topics
        self.case_sensitive = case_sensitive
        self.validate_output_enabled = validate_output

    def _matches_topic(self, text: str) -> bool:
        """Check if text contains any allowed topic."""
        if not self.case_sensitive:
            text = text.lower()
            topics = [t.lower() for t in self.topics]
        else:
            topics = self.topics

        return any(topic in text for topic in topics)

    async def validate_input(
        self, user_input: str, context: GuardrailContext
    ) -> str:
        if not self._matches_topic(user_input):
            raise InputViolation(
                f"Input must be about one of these topics: {', '.join(self.topics)}",
                guardrail_name=self.name,
                metadata={"allowed_topics": self.topics, "input": user_input},
            )
        return user_input

    async def validate_output(
        self, llm_output: str, context: GuardrailContext
    ) -> str:
        if self.validate_output_enabled and not self._matches_topic(llm_output):
            raise OutputViolation(
                f"Output must be about one of these topics: {', '.join(self.topics)}",
                guardrail_name=self.name,
                metadata={"allowed_topics": self.topics, "output": llm_output},
            )
        return llm_output


class ToxicContent(Guardrail):
    """Detects and blocks toxic or harmful content.

    This is a simple keyword-based implementation. For production use,
    consider using ML-based toxicity detection (e.g., Perspective API,
    Azure Content Safety, or open-source models).

    Example:
        @agent(provider=openai())
        @guardrail(ToxicContent(block_on_detection=True))
        async def safe_bot(user_input: str) -> str:
            '''Respond to: {user_input}'''

    Args:
        toxic_keywords: List of toxic keywords to detect
        block_on_detection: If True, raises violation; if False, just redacts
        replacement_text: Text to replace toxic content with
    """

    DEFAULT_TOXIC_KEYWORDS = [
        # This is a minimal example list
        "hate",
        "violent",
        "harmful",
        # In production, use a comprehensive list or ML model
    ]

    def __init__(
        self,
        toxic_keywords: List[str] = None,
        block_on_detection: bool = True,
        replacement_text: str = "[REDACTED]",
    ):
        self.toxic_keywords = toxic_keywords or self.DEFAULT_TOXIC_KEYWORDS
        self.block_on_detection = block_on_detection
        self.replacement_text = replacement_text

    def _detect_toxicity(self, text: str) -> List[str]:
        """Return list of detected toxic keywords."""
        text_lower = text.lower()
        detected = []
        for keyword in self.toxic_keywords:
            if keyword.lower() in text_lower:
                detected.append(keyword)
        return detected

    def _redact_toxicity(self, text: str) -> str:
        """Replace toxic keywords with replacement text."""
        result = text
        for keyword in self.toxic_keywords:
            # Case-insensitive replacement
            pattern = re.compile(re.escape(keyword), re.IGNORECASE)
            result = pattern.sub(self.replacement_text, result)
        return result

    async def validate_input(
        self, user_input: str, context: GuardrailContext
    ) -> str:
        detected = self._detect_toxicity(user_input)
        if detected:
            if self.block_on_detection:
                raise InputViolation(
                    f"Toxic content detected: {', '.join(detected)}",
                    guardrail_name=self.name,
                    metadata={"detected_keywords": detected},
                )
            else:
                return self._redact_toxicity(user_input)
        return user_input

    async def validate_output(
        self, llm_output: str, context: GuardrailContext
    ) -> str:
        detected = self._detect_toxicity(llm_output)
        if detected:
            if self.block_on_detection:
                raise OutputViolation(
                    f"Toxic content in output: {', '.join(detected)}",
                    guardrail_name=self.name,
                    metadata={"detected_keywords": detected},
                )
            else:
                return self._redact_toxicity(llm_output)
        return llm_output
