import re
from typing import List, Dict, Tuple

def parse_keywords(selector: str) -> List[str]:
    """Extracts search keywords/tokens from the failed selector."""
    # Find all word segments
    words = re.findall(r'[a-zA-Z0-9]+', selector)
    # Ignore common query/xpath selectors
    exclude = {"xpath", "css", "id", "class", "contains", "text", "and", "or", "div", "span", "input", "button", "a", "select", "ancestor", "sibling"}
    keywords = [w.lower() for w in words if w.lower() not in exclude]
    return keywords

def calculate_similarity(failed_selector: str, candidate: Dict) -> float:
    """Calculates similarity score [0.0 - 1.0] between selector and candidate element."""
    keywords = parse_keywords(failed_selector)
    if not keywords:
        return 0.0
    
    matched = 0
    total_checks = len(keywords)
    
    # Candidate text attributes
    fields = [
        candidate.get("id", ""),
        candidate.get("name", ""),
        candidate.get("data_test", ""),
        candidate.get("placeholder", ""),
        candidate.get("text", ""),
        candidate.get("className", "")
    ]
    
    for kw in keywords:
        found = False
        for f in fields:
            if f and kw in str(f).lower():
                found = True
                break
        if found:
            matched += 1
            
    if total_checks == 0:
        return 0.0
        
    score = matched / total_checks
    
    # Apply boosts for exact attribute match intersections
    failed_lower = failed_selector.lower()
    
    c_id = candidate.get("id")
    if c_id and c_id.lower() in failed_lower:
        score += 0.2
        
    c_name = candidate.get("name")
    if c_name and c_name.lower() in failed_lower:
        score += 0.2
        
    c_dt = candidate.get("data_test")
    if c_dt and c_dt.lower() in failed_lower:
        score += 0.3
        
    return min(score, 1.0)

def match_selectors(failed_selector: str, candidates: List[Dict], threshold: float = 0.5) -> List[Tuple[float, Dict]]:
    """Scores all candidate elements and returns a sorted list of matches above the threshold."""
    scored = []
    for c in candidates:
        score = calculate_similarity(failed_selector, c)
        if score >= threshold:
            scored.append((score, c))
    scored.sort(key=lambda x: x[0], reverse=True)
    return scored
