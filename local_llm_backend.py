"""Local LLM backend using Ollama for career report and resume generation."""

from __future__ import annotations

import os
import re
from typing import Dict, List

import requests


DEFAULT_OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1:8b")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")


CAREER_SYSTEM_PROMPT = (
    "You are a career intelligence engine. "
    "Return EXACTLY 6 segments separated by ';' in this order: "
    "Recommended Roles; Required Skills Gap; Project Recommendations; "
    "Resume Improvements; Company Targets; Timeline Strategy."
)

RESUME_SYSTEM_PROMPT = (
    "You are an ATS-focused resume writer. "
    "Return a clean one-page plain-text resume with sections: "
    "Name, Education, Skills, Projects, Experience, Achievements."
)


def _ollama_chat(system_prompt: str, user_prompt: str, model_name: str, timeout: int = 120) -> str:
    endpoint = f"{OLLAMA_BASE_URL}/api/chat"
    payload = {
        "model": model_name,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "stream": False,
        "options": {"temperature": 0.2},
    }
    response = requests.post(endpoint, json=payload, timeout=timeout)
    response.raise_for_status()
    body = response.json()
    return str(body.get("message", {}).get("content", "")).strip()


def _validate_career_segments(text: str) -> bool:
    if not text or ";" not in text:
        return False
    parts = [p.strip() for p in text.split(";") if p.strip()]
    return len(parts) >= 6


def generate_career_report_local(user_data: str, model_name: str = DEFAULT_OLLAMA_MODEL) -> str:
    prompt = (
        "Analyze this student profile and hiring context data.\n"
        "Give concise practical output in strict 6-segment semicolon format.\n\n"
        f"USER_DATA:\n{user_data}\n"
    )
    text = _ollama_chat(CAREER_SYSTEM_PROMPT, prompt, model_name=model_name)
    if _validate_career_segments(text):
        return text

    # Coerce if model did not follow exact delimiter format.
    chunks = [c.strip() for c in re.split(r"[\n;]+", text) if c.strip()]
    while len(chunks) < 6:
        chunks.append("Not enough signal from local model")
    return ";".join(chunks[:6])


def generate_resume_local(user_data: str, model_name: str = DEFAULT_OLLAMA_MODEL) -> str:
    prompt = (
        "Generate a role-targeted ATS resume from this data. Use quantified impact bullets where possible.\n\n"
        f"USER_DATA:\n{user_data}\n"
    )
    return _ollama_chat(RESUME_SYSTEM_PROMPT, prompt, model_name=model_name)


def run_local_all(user_data: str, model_name: str = DEFAULT_OLLAMA_MODEL) -> Dict[str, str]:
    return {
        "career_report": generate_career_report_local(user_data=user_data, model_name=model_name),
        "resume_text": generate_resume_local(user_data=user_data, model_name=model_name),
    }
