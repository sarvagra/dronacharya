"""Groq LLM backend for career intelligence."""

import os
import json
from typing import Optional

from groq import Groq

GROQ_BASE_URL = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

SYSTEM_PROMPT = (
    "You are a career intelligence engine.\n\n"
    "You must:\n"
    "- Analyze the given user data\n"
    "- Compare it with hiring trends dataset\n"
    "- Recommend optimal career path\n\n"
    "STRICT OUTPUT FORMAT:\n"
    "Return output in EXACT segments separated by ';'\n\n"
    "Segments order:\n"
    "1. Recommended Roles\n"
    "2. Required Skills Gap\n"
    "3. Project Recommendations\n"
    "4. Resume Improvements\n"
    "5. Company Targets\n"
    "6. Timeline Strategy\n\n"
    "Keep each segment concise but precise.\n"
    "No extra text outside segments."
)

RESUME_PROMPT = (
    "You are an ATS-optimized resume generator.\n\n"
    "Generate a professional one-page resume with:\n"
    "- Strong action verbs\n"
    "- Metrics-driven bullet points\n"
    "- Clean formatting\n\n"
    "Sections:\n"
    "- Name\n"
    "- Education\n"
    "- Skills\n"
    "- Projects\n"
    "- Experience\n"
    "- Achievements\n\n"
    "Tailor it EXACTLY to target roles inferred from user data.\n\n"
    "Ensure:\n"
    "- ATS score > 95\n"
    "- No fluff\n"
    "- Industry-standard formatting"
)


def _init_groq_client():
    """Initialize Groq client with API key."""
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise EnvironmentError("Set GROQ_API_KEY in environment")
    return Groq(api_key=api_key)


def _groq_chat(system_prompt: str, user_prompt: str, model: str = GROQ_MODEL) -> str:
    """Call Groq API with system and user prompts."""
    client = _init_groq_client()
    
    message = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.2,
        max_tokens=1024,
    )
    
    return message.choices[0].message.content.strip()


def generate_career_report(user_data: str) -> str:
    """Generate career recommendations using Groq."""
    user_prompt = (
        "USER DATA:\n"
        f"{user_data}\n\n"
        "TASK:\n"
        "Generate career recommendations based on the user profile and industry trends. "
        "Output EXACTLY in the 6-segment format separated by semicolons."
    )
    
    return _groq_chat(SYSTEM_PROMPT, user_prompt, model=GROQ_MODEL)


def generate_resume(user_data: str) -> str:
    """Generate ATS-optimized resume using Groq."""
    user_prompt = (
        "USER DATA:\n"
        f"{user_data}\n\n"
        "TASK:\n"
        "Generate a professional ATS-optimized resume from this user data."
    )
    
    return _groq_chat(RESUME_PROMPT, user_prompt, model=GROQ_MODEL)


def run_all(user_data: str) -> dict:
    """Generate both career report and resume."""
    try:
        career_report = generate_career_report(user_data)
        resume = generate_resume(user_data)
        
        return {
            "careerReport": career_report,
            "resume": resume,
            "error": None,
        }
    except Exception as e:
        return {
            "careerReport": None,
            "resume": None,
            "error": f"{type(e).__name__}: {str(e)}",
        }


# ============================================================================
# SPECIALIZED FEATURES FOR 6 BUTTONS
# ============================================================================


def generate_dream_cv(user_data: str) -> str:
    """Generate an ideal dream CV aligned with user profile and MNC expectations."""
    system_prompt = (
        "You are an elite resume strategist for top tech companies.\n"
        "Generate the DREAM CV - the ideal version showing maximum potential.\n"
        "Include:\n"
        "- Non-traditional achievements\n"
        "- Leadership examples\n"
        "- Quantified impact\n"
        "- 5-year vision projects\n"
        "- Open source & contributions\n"
        "Keep it aspirational but realistic."
    )
    
    user_prompt = (
        f"Based on this profile, generate an aspirational dream CV:\n{user_data}\n\n"
        "Output format: Professional resume with realistic dream achievements.\n"
        "Make it inspiring but achievable within 2-3 years."
    )
    
    return _groq_chat(system_prompt, user_prompt)


def generate_github_recommendations(user_data: str) -> str:
    """Generate specific GitHub actions and project showcasing strategies."""
    system_prompt = (
        "You are a GitHub profile strategist.\n"
        "Provide actionable GitHub optimization strategies including:\n"
        "- Contribution streak recommendations\n"
        "- Project portfolio structure\n"
        "- Skills to showcase per project\n"
        "- README best practices\n"
        "- Collaboration opportunities\n"
        "Make it specific and actionable."
    )
    
    user_prompt = (
        f"For this student profile, recommend GitHub strategy:\n{user_data}\n\n"
        "Provide 5-7 specific GitHub actions and project showcasing strategies.\n"
        "Focus on impressing top MNCs like Google, Microsoft, Amazon."
    )
    
    return _groq_chat(system_prompt, user_prompt)


def generate_project_suggestions(user_data: str) -> str:
    """Generate project suggestions based on user data and market trends."""
    system_prompt = (
        "You are a project ideation mentor for tech careers.\n"
        "Suggest specific, implementable projects that:\n"
        "- Build relevant skills\n"
        "- Are portfolio-worthy\n"
        "- Can be completed in 2-4 weeks\n"
        "- Are trending in industry\n"
        "- Align with target roles\n"
        "Provide tech stack and impact for each."
    )
    
    user_prompt = (
        f"Based on this student profile:\n{user_data}\n\n"
        "Suggest 4-5 portfolio-building projects that would impress MNCs.\n"
        "Include: Project name, description, tech stack, timeline, expected impact.\n"
        "Vary difficulty levels (beginner, intermediate, advanced)."
    )
    
    return _groq_chat(system_prompt, user_prompt)


def generate_strict_deadlines_tasks(user_data: str) -> str:
    """Generate strict, pinpoint tasks with official deadlines and certifications."""
    system_prompt = (
        "You are a career planning expert with knowledge of certifications and platforms.\n"
        "Create a strict action plan with:\n"
        "- Specific certifications (AWS, Google Cloud, Kubernetes, etc.)\n"
        "- Official learning platforms (Coursera, Udemy, Linux Academy)\n"
        "- Pinpoint skills to master\n"
        "- Realistic deadlines (weekly/monthly)\n"
        "- Measurable milestones\n"
        "- Success criteria\n"
        "Be specific about weeks and months."
    )
    
    user_prompt = (
        f"Create a strict action plan for this student:\n{user_data}\n\n"
        "Generate a detailed 6-month plan with:\n"
        "1. Week-by-week tasks (first 8 weeks)\n"
        "2. Official certifications to pursue\n"
        "3. Platforms/resources (with links/names)\n"
        "4. Skills to master with priority\n"
        "5. Monthly milestones and deadlines\n"
        "6. Success criteria for each milestone\n\n"
        "Format: Clear, actionable, with specific dates."
    )
    
    return _groq_chat(system_prompt, user_prompt)


def generate_current_openings_analysis(user_data: str) -> str:
    """Analyze job openings at top 15 MNCs based on user profile and CGPA."""
    system_prompt = (
        "You are an MNC hiring analyst with knowledge of top company recruitment.\n"
        "Analyze job openings at major companies:\n"
        "- Google, Microsoft, Amazon, Apple, Meta, Tesla\n"
        "- Amazon, Flipkart, OYO, Swiggy (India tech leaders)\n"
        "- JP Morgan, Goldman Sachs, Bank of America (Finance Tech)\n"
        "- VMware, Salesforce, Adobe, ServiceNow (Enterprise)\n\n"
        "For each company, analyze:\n"
        "- Typical CGPA requirements\n"
        "- Most common roles\n"
        "- Key skills requirements\n"
        "- Internship vs FTE pathways\n"
        "- Hiring season timeline"
    )
    
    user_prompt = (
        f"Based on this profile:\n{user_data}\n\n"
        "Analyze job openings at top 15 MNCs:\n"
        "1. How many roles match this CGPA?\n"
        "2. Which companies are actively hiring for similar profiles?\n"
        "3. What are the skill gaps for each company?\n"
        "4. Best pathway (intern → FTE or direct FTE)?\n"
        "5. Realistic timeline for each?\n\n"
        "Format: Company-wise analysis with actionability ratings."
    )
    
    return _groq_chat(system_prompt, user_prompt)


def generate_must_learn_topics(user_data: str) -> str:
    """Generate most important topics and tools to master for top MNCs."""
    system_prompt = (
        "You are a tech skills advisor for MNC entrance.\n"
        "Identify the most critical skills to master:\n"
        "- Based on latest hiring trends\n"
        "- Focus on top 15 MNCs\n"
        "- Prioritize by demand and impact\n"
        "- Include tools, frameworks, and conceptual topics\n"
        "- Separate by role type (SDE, DevOps, Data, ML, etc.)"
    )
    
    user_prompt = (
        f"For this student aiming for top MNCs:\n{user_data}\n\n"
        "Generate the top 15-20 must-learn topics. Include:\n"
        "1. Rank by priority (Critical, High, Medium)\n"
        "2. Why each is important\n"
        "3. Resources to learn (free/paid)\n"
        "4. Expected learning time\n"
        "5. How to demonstrate mastery in interviews\n"
        "6. Real-world application examples\n\n"
        "Format: Prioritized list with learning path."
    )
    
    return _groq_chat(system_prompt, user_prompt)


def evaluate_resume_ats(resume_text: str, user_data: str = "") -> dict:
    """Evaluate resume ATS quality and return score + grade + verdict."""
    system_prompt = (
        "You are an ATS evaluator for campus and early-career resumes. "
        "Return STRICT JSON with keys: score (0-100 int), grade (A|B|C), verdict (string), strengths (array), improvements (array)."
    )

    user_prompt = (
        "Evaluate this resume text and provide ATS assessment for student placements.\n\n"
        f"PROFILE CONTEXT:\n{user_data}\n\n"
        f"RESUME TEXT:\n{resume_text}\n\n"
        "Grading rubric: A=85-100 (strong), B=70-84 (decent), C=<70 (needs work)."
    )

    raw = _groq_chat(system_prompt, user_prompt)
    try:
        parsed = json.loads(raw)
        return {
            "score": int(parsed.get("score", 0)),
            "grade": str(parsed.get("grade", "C")).strip().upper()[:1],
            "verdict": str(parsed.get("verdict", "Needs improvement")).strip(),
            "strengths": parsed.get("strengths", []) if isinstance(parsed.get("strengths", []), list) else [],
            "improvements": parsed.get("improvements", []) if isinstance(parsed.get("improvements", []), list) else [],
        }
    except Exception:
        score = 75
        if len(resume_text.split()) > 350:
            score += 5
        if any(k in resume_text.lower() for k in ["project", "skills", "experience", "%", "built", "designed"]):
            score += 5
        score = max(40, min(95, score))
        grade = "A" if score >= 85 else ("B" if score >= 70 else "C")
        verdict = "Good resume quality" if grade in ["A", "B"] else "Resume needs improvement"
        return {
            "score": score,
            "grade": grade,
            "verdict": verdict,
            "strengths": ["Parsed from uploaded PDF"],
            "improvements": ["Add quantified impact bullets", "Improve keyword alignment to target role"],
        }

