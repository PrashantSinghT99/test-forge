"""
Automated Test Failure Classifier.

Categorizes test failures into structured taxonomy buckets (Assertion, Locator Issue, Timeout, Other)
and extracts target element selector strings from stack traces and exception messages.
"""

import re
from dataclasses import asdict, dataclass


@dataclass
class FailureResult:
    """
    Structured failure analysis outcome.

    Attributes:
        category (str): Standardized classification category (e.g. 'Assertion', 'Locator Issue', 'Timeout').
        message (str): Original raw exception message text.
        locator (str | None): Extracted target element selector, if identified.
        healed (bool): Whether the failure was successfully recovered via self-healing.
        healed_selector (str | None): Replacement selector used if healed.
    """

    category: str
    message: str
    locator: str | None
    healed: bool
    healed_selector: str | None = None

    def to_dict(self):
        """Converts dataclass instance into a JSON-serializable dictionary."""
        return asdict(self)


def classify_failure(
    exception_type: str, exception_message: str, traceback_str: str = ""
) -> FailureResult:
    """
    Analyses exception metadata to classify the failure type and extract selector details.

    Args:
        exception_type (str): Python class name of the exception (e.g. 'AssertionError', 'TimeoutError').
        exception_message (str): String representation of the exception.
        traceback_str (str): Full execution stack trace string (optional).

    Returns:
        FailureResult: Structured FailureResult object containing classification and extracted locator.
    """
    typename = exception_type.lower()
    msg = exception_message.lower()

    category = "Other"
    locator = None

    # Categorization rules
    if (
        "assertion" in typename
        or "assert" in msg
        or "assert" in traceback_str.lower()
        or "expect" in msg
    ):
        category = "Assertion"
    elif any(
        t in msg
        for t in [
            "locator",
            "selector",
            "waiting for locator",
            "waiting for selector",
            "unable to locate",
        ]
    ):
        category = "Locator Issue"
    elif "timeout" in typename or "timeout" in msg:
        category = "Timeout"

    # Extract selector/locator using regex from message or traceback
    loc_match = re.search(r'waiting for locator\("([^"]+)"\)', exception_message)
    if not loc_match:
        loc_match = re.search(r"waiting for locator\('([^']+)'\)", exception_message)
    if not loc_match:
        loc_match = re.search(r'selector\s+[\'"]([^\'"]+)[\'"]', exception_message)
    if not loc_match:
        loc_match = re.search(r'locator\("([^"]+)"\)', exception_message)
    if not loc_match:
        loc_match = re.search(r"locator\('([^']+)'\)", exception_message)
    if not loc_match and traceback_str:
        loc_match = re.search(r'locator\("([^"]+)"\)', traceback_str)
        if not loc_match:
            loc_match = re.search(r"locator\('([^']+)'\)", traceback_str)

    if loc_match:
        locator = loc_match.group(1)
        if category == "Other":
            category = "Locator Issue"

    return FailureResult(
        category=category,
        message=exception_message,
        locator=locator,
        healed=False,
        healed_selector=None,
    )
