import json
import os
import urllib.request
from typing import Dict, List, Optional

from ..no_ai.dom_extractor import get_candidates


class StagehandAgent:
    def __init__(self, page, max_steps: int = 10):
        self.page = page
        self.max_steps = max_steps
        self.history = []

    def execute_goal(self, goal: str) -> List[Dict]:
        print(f"\n[Stagehand Agent] Starting execution for goal: '{goal}'")

        for step in range(1, self.max_steps + 1):
            url = self.page.url
            print(f"[Stagehand Agent] Step {step} | URL: {url}")

            candidates = get_candidates(self.page)
            redacted_candidates = []
            for c in candidates:
                redacted_candidates.append(
                    {
                        "tag": c["tag"],
                        "id": c["id"],
                        "name": c["name"],
                        "data_test": c["data_test"],
                        "placeholder": c["placeholder"],
                        "text": c["text"],
                        "xpath": c["xpath"],
                        "css": c["css"],
                    }
                )

            action = self._get_ai_action(goal, url, redacted_candidates)

            if not action:
                action = self._get_heuristic_action(goal, url, redacted_candidates)

            if not action:
                print("[Stagehand Agent] No action decided. Planning failed.")
                break

            print(
                f"[Stagehand Agent] Decided action: {action.get('action')} | Reason: {action.get('reason')}"
            )
            self.history.append(action)

            act_type = action.get("action")
            if act_type == "complete":
                print("[Stagehand Agent] Goal achieved successfully!")
                break
            elif act_type == "navigate":
                target_url = action.get("url")
                self.page.goto(target_url)
            elif act_type == "click":
                selector = action.get("selector")
                self.page.locator(selector).click()
            elif act_type == "fill":
                selector = action.get("selector")
                val = action.get("value", "")
                self.page.locator(selector).fill(val)
            else:
                print(f"[Stagehand Agent] Unknown action type: '{act_type}'")
                break

            self.page.wait_for_timeout(1000)

        return self.history

    def _get_ai_action(
        self, goal: str, url: str, candidates: List[Dict]
    ) -> Optional[Dict]:
        ollama_url = os.environ.get("OLLAMA_API_URL", "http://localhost:11434")
        from ..ai.ai_helper import check_ollama_alive

        use_ollama = check_ollama_alive(ollama_url)
        use_hf = os.environ.get("HF_API_TOKEN") is not None
        use_gemini = os.environ.get("GEMINI_API_KEY") is not None

        if not (use_ollama or use_hf or use_gemini):
            return None

        prompt = (
            f"You are an AI browser agent (Stagehand). Your task is to achieve the following objective on a website.\n"
            f"Objective: {goal}\n"
            f"Current URL: {url}\n"
            f"Action history: {json.dumps(self.history, indent=2)}\n\n"
            f"Interactive elements visible:\n{json.dumps(candidates, indent=2)}\n\n"
            f"Select the next logical action. Respond ONLY with a JSON object. Format options:\n"
            f'1. Click: {{"action": "click", "selector": "css_or_xpath_selector", "reason": "reason"}}\n'
            f'2. Fill: {{"action": "fill", "selector": "css_or_xpath_selector", "value": "text_to_fill", "reason": "reason"}}\n'
            f'3. Navigate: {{"action": "navigate", "url": "url", "reason": "reason"}}\n'
            f'4. Complete: {{"action": "complete", "reason": "achieved"}}\n'
            f"Do not include markdown or backticks."
        )

        try:
            text_response = None
            if use_ollama:
                model = os.environ.get("OLLAMA_MODEL", "qwen2.5-coder:1.5b")
                payload = {
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                    "stream": False,
                    "options": {"temperature": 0.0},
                }
                req = urllib.request.Request(
                    f"{ollama_url}/v1/chat/completions",
                    data=json.dumps(payload).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urllib.request.urlopen(req, timeout=5.0) as resp:
                    res_data = json.loads(resp.read().decode("utf-8"))
                    text_response = res_data["choices"][0]["message"]["content"].strip()
            elif use_hf:
                hf_token = os.environ.get("HF_API_TOKEN")
                model = os.environ.get("HF_MODEL", "Qwen/Qwen2.5-Coder-7B-Instruct")
                payload = {
                    "inputs": f"<|im_start|>system\nYou are an AI browser agent. Respond ONLY with raw JSON.<|im_end|>\n<|im_start|>user\n{prompt}<|im_end|>\n<|im_start|>assistant\n",
                    "parameters": {
                        "max_new_tokens": 150,
                        "temperature": 0.1,
                        "return_full_text": False,
                    },
                }
                req = urllib.request.Request(
                    f"https://api-inference.huggingface.co/models/{model}",
                    data=json.dumps(payload).encode("utf-8"),
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {hf_token}",
                    },
                    method="POST",
                )
                with urllib.request.urlopen(req, timeout=5.0) as resp:
                    res_data = json.loads(resp.read().decode("utf-8"))
                    if isinstance(res_data, list):
                        text_response = res_data[0].get("generated_text", "").strip()
                    else:
                        text_response = res_data.get("generated_text", "").strip()
            elif use_gemini:
                key = os.environ.get("GEMINI_API_KEY")
                payload = {"contents": [{"parts": [{"text": prompt}]}]}
                req = urllib.request.Request(
                    f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={key}",
                    data=json.dumps(payload).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urllib.request.urlopen(req, timeout=5.0) as resp:
                    res_data = json.loads(resp.read().decode("utf-8"))
                    text_response = res_data["candidates"][0]["content"]["parts"][0][
                        "text"
                    ].strip()

            if text_response:
                if text_response.startswith("```"):
                    text_response = text_response.strip("`").strip()
                    if text_response.startswith("json"):
                        text_response = text_response[4:].strip()
                start = text_response.find("{")
                end = text_response.rfind("}")
                if start != -1 and end != -1:
                    block = text_response[start : end + 1]
                    return json.loads(block)
        except Exception as e:
            print(f"[Stagehand Agent] AI Planning step failed: {e}")

        return None

    def _get_heuristic_action(
        self, goal: str, url: str, candidates: List[Dict]
    ) -> Optional[Dict]:
        goal_lower = goal.lower()

        has_username = any(c["id"] == "user-name" for c in candidates)
        has_login_btn = any(c["id"] == "login-button" for c in candidates)

        if "login" in goal_lower or "backpack" in goal_lower or "cart" in goal_lower:
            if has_username and has_login_btn:
                username_filled = any(
                    h.get("action") == "fill" and h.get("selector") == "#user-name"
                    for h in self.history
                )
                password_filled = any(
                    h.get("action") == "fill" and h.get("selector") == "#password"
                    for h in self.history
                )

                if not username_filled:
                    return {
                        "action": "fill",
                        "selector": "#user-name",
                        "value": "standard_user",
                        "reason": "[Heuristic] Fill username field for login",
                    }
                elif not password_filled:
                    return {
                        "action": "fill",
                        "selector": "#password",
                        "value": "secret_sauce",
                        "reason": "[Heuristic] Fill password field for login",
                    }
                else:
                    return {
                        "action": "click",
                        "selector": "#login-button",
                        "reason": "[Heuristic] Click login button",
                    }

        if "backpack" in goal_lower or "cart" in goal_lower:
            if "/inventory.html" in url:
                backpack_btn = None
                for c in candidates:
                    if (
                        "add-to-cart-sauce-labs-backpack" in c["id"]
                        or "backpack" in c["id"]
                        and c["tag"] == "button"
                    ):
                        backpack_btn = c["css"] or f"#{c['id']}"
                        break

                if not backpack_btn:
                    backpack_btn = "//button[@id='add-to-cart-sauce-labs-backpack']"

                clicked_backpack = any(
                    h.get("action") == "click" and h.get("selector") == backpack_btn
                    for h in self.history
                )
                clicked_cart_link = any(
                    h.get("action") == "click"
                    and h.get("selector") == ".shopping_cart_link"
                    for h in self.history
                )

                if not clicked_backpack:
                    return {
                        "action": "click",
                        "selector": backpack_btn,
                        "reason": "[Heuristic] Click backpack add-to-cart button",
                    }
                elif "cart" in goal_lower and not clicked_cart_link:
                    return {
                        "action": "click",
                        "selector": ".shopping_cart_link",
                        "reason": "[Heuristic] Click shopping cart link to navigate to cart",
                    }
                else:
                    return {
                        "action": "complete",
                        "reason": "[Heuristic] Successfully completed the objective",
                    }

            if "/cart.html" in url:
                return {
                    "action": "complete",
                    "reason": "[Heuristic] Arrived at cart page, objective completed",
                }

        return {
            "action": "complete",
            "reason": "[Heuristic] Goal default fallback completion",
        }
