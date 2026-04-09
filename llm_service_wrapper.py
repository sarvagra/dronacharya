import os
from typing import Dict

from groq_llm_backend import generate_career_report, generate_resume, run_all as groq_run_all


def run_career_engine(user_data: str) -> str:
    """Return semicolon-separated 6-segment career guidance text."""
    return generate_career_report(user_data)


def run_resume_engine(user_data: str) -> str:
    """Return ATS-oriented plain text resume."""
    return generate_resume(user_data)


def run_all(user_data: str) -> Dict[str, str]:
    """Single-call wrapper for report + resume using Groq."""
    result = groq_run_all(user_data)
    return {
        "career_report": result["careerReport"],
        "resume_text": result["resume"],
    }


if __name__ == "__main__":
    sample_user_data = (
        "name: Alex; cgpa: 8.2; skills: python, sql, power bi; "
        "projects: churn prediction, sales dashboard; "
        "aim: data + product roles in fintech"
    )

    try:
        outputs = run_all(sample_user_data)
        print("CAREER REPORT")
        print(outputs["career_report"])
        print("\nRESUME")
        print(outputs["resume_text"])
    except Exception as exc:
        print(f"Error: {exc}")
