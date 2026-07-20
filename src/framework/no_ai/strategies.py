"""
Heuristic Matching Strategies for Deterministic Self-Healing.

Provides token extraction, string similarity algorithms, attribute intersection scoring,
and threshold ranking to select candidate replacement locators without external API calls.
"""

import re
from typing import Dict, List, Tuple


def parse_keywords(selector: str) -> List[str]:
    """
    Extracts semantic search keywords/tokens from a broken selector string.

    Args:
        selector (str): The failed XPath or CSS selector string.

    Returns:
        List[str]: List of lower-case alphanumeric tokens, excluding generic XPath/CSS keywords.
    """
    # Find all word segments
    words = re.findall(r"[a-zA-Z0-9]+", selector)
    # Ignore common query/xpath selectors
    exclude = {
        "xpath",
        "css",
        "id",
        "class",
        "contains",
        "text",
        "and",
        "or",
        "div",
        "span",
        "input",
        "button",
        "a",
        "select",
        "ancestor",
        "sibling",
    }
    keywords = [w.lower() for w in words if w.lower() not in exclude]
    return keywords


def calculate_similarity(failed_selector: str, candidate: Dict) -> float:
    """
    Calculates a similarity score [0.0 - 1.0] between a failed selector and a DOM candidate element.

    Args:
        failed_selector (str): The broken selector string.
        candidate (Dict): DOM element attribute dictionary extracted from page.

    Returns:
        float: Similarity confidence score between 0.0 and 1.0.
    """
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
        candidate.get("className", ""),
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


def match_selectors(
    failed_selector: str, candidates: List[Dict], threshold: float = 0.5
) -> List[Tuple[float, Dict]]:
    """
    Scores all candidate elements and returns a sorted list of matches above the given threshold.

    Args:
        failed_selector (str): The broken selector string.
        candidates (List[Dict]): List of candidate elements extracted from page DOM.
        threshold (float): Minimum confidence score threshold (default 0.5).

    Returns:
        List[Tuple[float, Dict]]: Ranked list of (score, candidate_dict) tuples sorted descending by score.
    """
    scored = []
    for c in candidates:
        score = calculate_similarity(failed_selector, c)
        if score >= threshold:
            scored.append((score, c))
    scored.sort(key=lambda x: x[0], reverse=True)
    return scored
