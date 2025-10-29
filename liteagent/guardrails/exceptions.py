"""Exception types for guardrail violations."""

from typing import Optional


class GuardrailViolation(Exception):
    """Base exception for guardrail violations.

    Raised when a guardrail detects a policy violation.
    Can be caught and handled by application code.

    Attributes:
        message: Human-readable error message
        guardrail_name: Name of the guardrail that raised the violation
        metadata: Additional context about the violation
    """

    def __init__(
        self,
        message: str,
        guardrail_name: Optional[str] = None,
        metadata: Optional[dict] = None,
    ):
        self.message = message
        self.guardrail_name = guardrail_name
        self.metadata = metadata or {}
        super().__init__(message)

    def __str__(self) -> str:
        if self.guardrail_name:
            return f"[{self.guardrail_name}] {self.message}"
        return self.message


class InputViolation(GuardrailViolation):
    """Raised when input validation fails.

    This indicates the user input violated a guardrail policy
    before being sent to the LLM.
    """

    pass


class OutputViolation(GuardrailViolation):
    """Raised when output validation fails.

    This indicates the LLM output violated a guardrail policy
    before being returned to the user.
    """

    pass
