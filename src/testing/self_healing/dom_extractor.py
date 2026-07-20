"""
DOM Candidate Extractor for Self-Healing Engine.

Executes client-side JavaScript in the browser context via Playwright to extract
interactive element attributes, unique XPaths, and CSS paths while redacting sensitive fields.
"""
from typing import List, Dict, Any

def get_candidates(page) -> List[Dict[str, Any]]:
    """
    Extracts all candidate interactive elements from the active page DOM.

    Args:
        page (Page): Active Playwright Page instance.

    Returns:
        List[Dict[str, Any]]: List of dictionary representations of DOM elements containing:
            - tag, id, name, data_test, placeholder, text, className, xpath, css.

    Notes:
        - Redacts sensitive field values (password, hidden inputs).
        - Truncates text content to maximum 100 characters.
    """
    js_code = """
    () => {
        function getXPath(element) {
            if (element.id) {
                return `//*[@id="${element.id}"]`;
            }
            if (element === document.body) {
                return '/html/body';
            }
            let ix = 0;
            let siblings = element.parentNode ? element.parentNode.childNodes : [];
            for (let i = 0; i < siblings.length; i++) {
                let sibling = siblings[i];
                if (sibling === element) {
                    return getXPath(element.parentNode) + '/' + element.tagName.toLowerCase() + '[' + (ix + 1) + ']';
                }
                if (sibling.nodeType === 1 && sibling.tagName === element.tagName) {
                    ix++;
                }
            }
            return '';
        }
        function getCSS(element) {
            if (element.id) {
                return `#${element.id}`;
            }
            let path = element.tagName.toLowerCase();
            if (element.className) {
                let classes = Array.from(element.classList)
                    .filter(c => c && typeof c === 'string' && !c.includes(':') && !c.includes('[') && !c.includes(']'))
                    .join('.');
                if (classes) {
                    path += '.' + classes;
                }
            }
            return path;
        }
        const candidates = [];
        const tags = ['input', 'button', 'a', 'select', 'textarea'];
        for (const tag of tags) {
            const elems = document.querySelectorAll(tag);
            for (const el of elems) {
                let typeAttr = el.getAttribute('type') || '';
                let val = '';
                // Redact values for password, secret inputs
                if (typeAttr !== 'password' && typeAttr !== 'hidden') {
                    val = el.value || '';
                }
                candidates.push({
                    tag: tag,
                    id: el.id || '',
                    name: el.getAttribute('name') || '',
                    data_test: el.getAttribute('data-test') || el.getAttribute('data-testid') || '',
                    placeholder: el.getAttribute('placeholder') || '',
                    text: (el.innerText || val).substring(0, 100),
                    className: el.className || '',
                    xpath: getXPath(el),
                    css: getCSS(el)
                });
            }
        }
        return candidates;
    }
    """
    try:
        return page.evaluate(js_code)
    except Exception as e:
        print(f"[DOM Extractor] Error extracting candidates: {e}")
        return []
