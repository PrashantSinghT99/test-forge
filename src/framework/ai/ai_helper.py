"""
AI Multi-Provider Locator Healing & Routing Client.

Routes broken selector healing requests to available LLM providers in priority order:
1. Local Ollama (qwen2.5-coder:1.5b on http://localhost:11434)
2. Hugging Face Serverless API (Qwen/Qwen2.5-Coder-7B-Instruct via HF_API_TOKEN)
3. Gemini API (gemini-2.5-flash via GEMINI_API_KEY)

If all AI providers are unavailable, gracefully returns None to allow local heuristic fallback.
"""

import json
import os
import urllib.error
import urllib.request
from typing import Dict, List, Optional

_HEALING_CACHE: Dict[str, str] = {}


def check_ollama_alive(url: str = "http://localhost:11434") -> bool:
    """Checks if a local Ollama server instance is responding."""
    try:
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=1.0) as conn:
            return conn.status == 200
    except Exception:
        return False


def call_ollama(
    failed_selector: str, candidates: List[Dict], url: str = "http://localhost:11434"
) -> Optional[str]:
    print("[AI Helper] Querying local Ollama server...")
    model = os.environ.get("OLLAMA_MODEL", "qwen2.5-coder:1.5b")

    prompt = (
        f"You are a test automation healing assistant. A locator failed to find an element in a Playwright test.\n"
        f"Failed selector: '{failed_selector}'\n"
        f"Candidate elements on page:\n{json.dumps(candidates, indent=2)}\n\n"
        f"Choose the best candidate. Respond ONLY with a JSON object:\n"
        f'{{"best_match_xpath": "xpath", "best_match_css": "css", "reason": "reason"}}\n'
        f"Do not include markdown or backticks."
    )

    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False,
        "options": {"temperature": 0.0},
    }

    req = urllib.request.Request(
        f"{url}/v1/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=5.0) as response:
            res_data = json.loads(response.read().decode("utf-8"))
            text = res_data["choices"][0]["message"]["content"].strip()
            return parse_json_response(text)
    except Exception as e:
        print(f"[AI Helper] Ollama call failed: {e}")
        return None


def call_huggingface(
    failed_selector: str, candidates: List[Dict], token: str
) -> Optional[str]:
    print("[AI Helper] Querying Hugging Face Serverless API...")
    model = os.environ.get("HF_MODEL", "Qwen/Qwen2.5-Coder-7B-Instruct")

    prompt = (
        f"<|im_start|>system\nYou are a test automation healing assistant. Choose the best candidate to replace the failed selector. Respond ONLY with a JSON object. Do not include markdown.<|im_end|>\n"
        f"<|im_start|>user\n"
        f"Failed selector: '{failed_selector}'\n"
        f"Candidates:\n{json.dumps(candidates, indent=2)}\n\n"
        f"Respond in format:\n"
        f'{{"best_match_xpath": "xpath", "best_match_css": "css", "reason": "reason"}}\n'
        f"<|im_end|>\n"
        f"<|im_start|>assistant\n"
    )

    payload = {
        "inputs": prompt,
        "parameters": {
            "max_new_tokens": 150,
            "temperature": 0.1,
            "return_full_text": False,
        },
    }

    url = f"https://api-inference.huggingface.co/models/{model}"
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {token}",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=5.0) as response:
            res_data = json.loads(response.read().decode("utf-8"))
            text = ""
            if isinstance(res_data, list) and len(res_data) > 0:
                text = res_data[0].get("generated_text", "").strip()
            elif isinstance(res_data, dict):
                text = res_data.get("generated_text", "").strip()
            return parse_json_response(text)
    except Exception as e:
        print(f"[AI Helper] Hugging Face call failed: {e}")
        return None


def call_gemini(
    failed_selector: str, candidates: List[Dict], api_key: str
) -> Optional[str]:
    print("[AI Helper] Querying Gemini API...")
    prompt = {
        "contents": [
            {
                "parts": [
                    {
                        "text": (
                            f"You are a test automation healing assistant. A locator failed to find an element in a Playwright test.\n"
                            f"Failed selector: '{failed_selector}'\n"
                            f"Candidates:\n{json.dumps(candidates, indent=2)}\n\n"
                            f"Choose the best candidate. Respond ONLY with a JSON object in this format:\n"
                            f'{{"best_match_xpath": "xpath", "best_match_css": "css", "reason": "reason"}}\n'
                            f"Do not include markdown or backticks."
                        )
                    }
                ]
            }
        ]
    }

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
    req = urllib.request.Request(
        url,
        data=json.dumps(prompt).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=5.0) as response:
            res_data = json.loads(response.read().decode("utf-8"))
            text = res_data["candidates"][0]["content"]["parts"][0]["text"].strip()
            return parse_json_response(text)
    except Exception as e:
        print(f"[AI Helper] Gemini call failed: {e}")
        return None


def parse_json_response(text: str) -> Optional[str]:
    if text.startswith("```"):
        text = text.strip("`").strip()
        if text.startswith("json"):
            text = text[4:].strip()

    try:
        data = json.loads(text)
        xpath = data.get("best_match_xpath")
        css = data.get("best_match_css")
        return xpath or css
    except Exception:
        try:
            start = text.find("{")
            end = text.rfind("}")
            if start != -1 and end != -1:
                block = text[start : end + 1]
                data = json.loads(block)
                return data.get("best_match_xpath") or data.get("best_match_css")
        except Exception:
            pass
    return None


def suggest_locator(failed_selector: str, candidates: List[Dict]) -> Optional[str]:
    if failed_selector in _HEALING_CACHE:
        print(f"[AI Helper] Cache hit for failed selector: '{failed_selector}'")
        return _HEALING_CACHE[failed_selector]

    result = None

    # Priority 1: Ollama
    ollama_url = os.environ.get("OLLAMA_API_URL", "http://localhost:11434")
    if check_ollama_alive(ollama_url):
        result = call_ollama(failed_selector, candidates, ollama_url)

    # Priority 2: Hugging Face
    if not result:
        hf_token = os.environ.get("HF_API_TOKEN")
        if hf_token:
            result = call_huggingface(failed_selector, candidates, hf_token)

    # Priority 3: Gemini
    if not result:
        gemini_key = os.environ.get("GEMINI_API_KEY")
        if gemini_key:
            result = call_gemini(failed_selector, candidates, gemini_key)

    if result:
        print(f"[AI Helper] Successfully suggested alternative locator: '{result}'")
        _HEALING_CACHE[failed_selector] = result
    else:
        print("[AI Helper] No AI suggestion was generated (or all providers failed).")

    return result
