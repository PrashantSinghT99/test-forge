import time
from pathlib import Path
from playwright.sync_api import Locator
from .dom_extractor import get_candidates
from .strategies import match_selectors

class HealingLocator:
    def __init__(self, healing_page, original_locator, selector):
        self._healing_page = healing_page
        self._original = original_locator
        self._selector = selector

    def __getattr__(self, name):
        return getattr(self._original, name)

    @property
    def __class__(self):
        return Locator

    def click(self, **kwargs):
        return self._run_action_with_healing("click", lambda loc: loc.click(**kwargs))

    def fill(self, value, **kwargs):
        return self._run_action_with_healing("fill", lambda loc: loc.fill(value, **kwargs))

    def clear(self, **kwargs):
        return self._run_action_with_healing("clear", lambda loc: loc.clear(**kwargs))

    def type(self, text, **kwargs):
        return self._run_action_with_healing("type", lambda loc: loc.type(text, **kwargs))

    def press(self, key, **kwargs):
        return self._run_action_with_healing("press", lambda loc: loc.press(key, **kwargs))

    def check(self, **kwargs):
        return self._run_action_with_healing("check", lambda loc: loc.check(**kwargs))

    def uncheck(self, **kwargs):
        return self._run_action_with_healing("uncheck", lambda loc: loc.uncheck(**kwargs))

    def select_option(self, values=None, **kwargs):
        return self._run_action_with_healing("select_option", lambda loc: loc.select_option(values, **kwargs))

    def _run_action_with_healing(self, action_name, action_fn, *args, **kwargs):
        if not self._healing_page.enabled:
            return action_fn(self._original)

        try:
            return action_fn(self._original)
        except Exception as primary_exc:
            print(f"\n[Self-Healing] Primary locator '{self._selector}' failed for '{action_name}': {primary_exc}")
            
            if len(self._healing_page.healed_attempts) >= self._healing_page.max_attempts:
                print("[Self-Healing] Max healing attempts limit reached. Propagating error.")
                raise primary_exc

            import sys, os
            # Store heal screenshots under branch report folder so they survive clear_previous()
            _branch = os.environ.get("PYTEST_BRANCH", "")
            if _branch:
                screenshots_dir = Path("reports") / _branch / "screenshots"
            else:
                screenshots_dir = Path("screenshots")
            screenshots_dir = screenshots_dir.resolve()
            screenshots_dir.mkdir(parents=True, exist_ok=True)
            ts = int(time.time())
            before_path = screenshots_dir / f"before_heal_{ts}.png"
            try:
                self._healing_page.page.screenshot(path=str(before_path), timeout=5000)
                print(f"[Self-Healing] Captured 'before' screenshot: {before_path}", file=sys.stderr)
            except Exception as se:
                print(f"[Self-Healing] Failed to capture before screenshot: {se}", file=sys.stderr)

            candidates = get_candidates(self._healing_page.page)
            if not candidates:
                print("[Self-Healing] No DOM candidates extracted. Propagating error.", file=sys.stderr)
                raise primary_exc

            fallbacks = []
            
            if self._healing_page.use_ai:
                try:
                    from ..ai_helper import suggest_locator
                    ai_suggestion = suggest_locator(self._selector, candidates)
                    if ai_suggestion:
                        print(f"[Self-Healing] AI suggested fallback: '{ai_suggestion}'", file=sys.stderr)
                        fallbacks.append(ai_suggestion)
                except Exception as ae:
                    print(f"[Self-Healing] AI suggestion failed: {ae}", file=sys.stderr)

            # Heuristics matches
            scored_matches = match_selectors(self._selector, candidates, threshold=0.5)
            for score, c in scored_matches:
                xpath = c.get("xpath")
                css = c.get("css")
                if xpath and xpath not in fallbacks:
                    fallbacks.append(xpath)
                if css and css not in fallbacks:
                    fallbacks.append(css)

            if not fallbacks:
                print("[Self-Healing] No suitable fallback selectors found. Propagating error.", file=sys.stderr)
                raise primary_exc

            for fb in fallbacks:
                try:
                    print(f"[Self-Healing] Attempting fallback: '{fb}'", file=sys.stderr)
                    fallback_locator = self._healing_page.page.locator(fb)
                    res = action_fn(fallback_locator)
                    print(f"[Self-Healing] Success! Resolved '{self._selector}' using '{fb}'", file=sys.stderr)

                    after_path = screenshots_dir / f"after_heal_{ts}.png"
                    try:
                        self._healing_page.page.screenshot(path=str(after_path), timeout=5000)
                        print(f"[Self-Healing] Captured 'after' screenshot: {after_path}", file=sys.stderr)
                    except Exception as se:
                        print(f"[Self-Healing] Failed to capture after screenshot: {se}", file=sys.stderr)

                    self._healing_page.healed_attempts.append({
                        "original_selector": self._selector,
                        "healed_selector": fb,
                        "action": action_name,
                        "test_name": self._healing_page.test_name,
                        "timestamp": time.time(),
                        "before_screenshot": str(before_path),
                        "after_screenshot": str(after_path)
                    })
                    return res
                except Exception as fb_exc:
                    print(f"[Self-Healing] Fallback '{fb}' failed: {fb_exc}")

            print("[Self-Healing] All fallbacks failed. Propagating original error.")
            raise primary_exc


class HealingPage:
    def __init__(self, page, test_name="", enabled=True, use_ai=False, max_attempts=3):
        self.page = page
        self.test_name = test_name
        self.enabled = enabled
        self.use_ai = use_ai
        self.max_attempts = max_attempts
        self.healed_attempts = []

    def locator(self, selector, **kwargs):
        loc = self.page.locator(selector, **kwargs)
        return HealingLocator(self, loc, selector)

    def __getattr__(self, name):
        return getattr(self.page, name)
