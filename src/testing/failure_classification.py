from dataclasses import dataclass, asdict
import re

@dataclass
class FailureResult:
    category: str
    message: str
    locator: str | None
    healed: bool
    healed_selector: str | None = None
    
    def to_dict(self):
        return asdict(self)

def classify_failure(exception_type: str, exception_message: str, traceback_str: str = "") -> FailureResult:
    typename = exception_type.lower()
    msg = exception_message.lower()
    
    category = "Other"
    locator = None
    
    # Categorization rules
    if "assertion" in typename or "assert" in msg or "assert" in traceback_str.lower() or "expect" in msg:
        category = "Assertion"
    elif any(t in msg for t in ["locator", "selector", "waiting for locator", "waiting for selector", "unable to locate"]):
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
        healed_selector=None
    )
