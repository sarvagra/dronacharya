"""Career profile backend with recommendation, fake-job detection and dataset refresh."""

from __future__ import annotations

import ast
import base64
import io
import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple
from urllib.parse import urlparse

import pandas as pd
from pypdf import PdfReader
try:
    from pdf2image import convert_from_bytes
except Exception:
    convert_from_bytes = None

try:
    import pytesseract
except Exception:
    pytesseract = None
from dotenv import load_dotenv
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

from llm_service_wrapper import run_all
from groq_llm_backend import evaluate_resume_ats
from scraper_service import scrape_jobs_from_urls

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
CORS(app)

BASE_DIR = Path(__file__).resolve().parent
DATA_PATH = BASE_DIR / "Data" / "mnc_jobs_dataset.csv"
PROFILES_DIR = BASE_DIR / "submitted_profiles"
PROFILES_DIR.mkdir(exist_ok=True)


def _as_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _parse_skill_list(raw: Any) -> List[str]:
    if raw is None:
        return []
    if isinstance(raw, list):
        return [str(x).strip().lower() for x in raw if str(x).strip()]

    text = str(raw).strip()
    if not text:
        return []

    try:
        parsed = ast.literal_eval(text)
        if isinstance(parsed, list):
            return [str(x).strip().lower() for x in parsed if str(x).strip()]
    except (ValueError, SyntaxError):
        pass

    return [x.strip().lower() for x in re.split(r"[,|/]", text) if x.strip()]


def _parse_cgpa_requirement(raw: Any) -> float:
    text = str(raw or "").strip().lower()
    nums = [float(x) for x in re.findall(r"\d+(?:\.\d+)?", text)]
    if not nums:
        return 7.0
    if "-" in text and len(nums) >= 2:
        return sum(nums[:2]) / 2.0
    return nums[0]


def _safe_filename_email(email: str) -> str:
    safe = re.sub(r"[^a-zA-Z0-9._-]", "_", email or "unknown")
    return safe[:80] or "unknown"


def load_jobs_df() -> pd.DataFrame:
    if not DATA_PATH.exists():
        raise FileNotFoundError(f"Dataset not found at {DATA_PATH}")

    df = pd.read_csv(DATA_PATH)
    if "industry/domain" in df.columns and "domain" not in df.columns:
        df = df.rename(columns={"industry/domain": "domain"})

    required_cols = [
        "company_name",
        "domain",
        "job_role",
        "job_type",
        "required_skills",
        "cgpa_requirement",
        "job_description",
        "salary_range",
        "source",
        "source_url",
    ]
    for col in required_cols:
        if col not in df.columns:
            df[col] = ""

    for col in required_cols:
        df[col] = df[col].fillna("").astype(str)

    return df[required_cols]


def _extract_user_skills(personal_info: Dict[str, Any]) -> List[str]:
    rating_keys = {
        "dsa": "dsa",
        "webDev": "web development",
        "mlAi": "machine learning",
        "dbms": "dbms",
        "os": "operating systems",
        "networking": "computer networks",
    }
    skills = []
    for key, label in rating_keys.items():
        if _as_float(personal_info.get(key, 0), 0) >= 3:
            skills.append(label)

    text_buckets = [
        personal_info.get("certifications", ""),
        personal_info.get("aim", ""),
        personal_info.get("extraSkills", ""),
    ]
    extra = " ".join(str(x) for x in text_buckets).lower()
    known = [
        "python",
        "java",
        "c++",
        "sql",
        "docker",
        "kubernetes",
        "aws",
        "gcp",
        "azure",
        "react",
        "node",
        "tensorflow",
        "pytorch",
        "tableau",
        "power bi",
        "git",
    ]
    for skill in known:
        if skill in extra:
            skills.append(skill)

    return sorted(set(skills))


def _profile_to_query(personal_info: Dict[str, Any], companies: List[str]) -> str:
    domains = personal_info.get("domains", [])
    if isinstance(domains, str):
        domains = [domains]

    sections = [
        str(personal_info.get("aim", "")),
        " ".join(domains),
        " ".join(companies),
        str(personal_info.get("branch", "")),
    ]
    return " ".join(sections).lower()


def _score_job_match(row: pd.Series, query: str, user_skills: List[str], user_cgpa: float) -> float:
    text = " ".join(
        [
            row.get("company_name", ""),
            row.get("domain", ""),
            row.get("job_role", ""),
            row.get("job_description", ""),
        ]
    ).lower()

    token_hits = sum(1 for tok in query.split() if len(tok) > 2 and tok in text)
    required_skills = _parse_skill_list(row.get("required_skills", ""))
    overlap = len(set(required_skills).intersection(set(user_skills)))
    cgpa_req = _parse_cgpa_requirement(row.get("cgpa_requirement", ""))
    cgpa_score = 3.0 if user_cgpa >= cgpa_req else max(-2.0, user_cgpa - cgpa_req)
    quality_penalty = -2.0 if "%pdf" in row.get("job_description", "").lower() else 0.0

    return (token_hits * 0.35) + (overlap * 1.8) + cgpa_score + quality_penalty


def _top_matches(df: pd.DataFrame, query: str, user_skills: List[str], user_cgpa: float, limit: int = 20) -> pd.DataFrame:
    scored = df.copy()
    scored["_score"] = scored.apply(lambda r: _score_job_match(r, query, user_skills, user_cgpa), axis=1)
    return scored.sort_values("_score", ascending=False).head(limit)


def _salary_hint(rows: pd.DataFrame) -> str:
    if rows.empty:
        return "6-12 LPA (insufficient direct matches)"
    salary_texts = rows["salary_range"].astype(str).tolist()
    compact = [s for s in salary_texts if s and s.lower() != "nan"]
    if not compact:
        return "6-12 LPA (salary not listed in dataset)"
    return "; ".join(compact[:3])


def _generate_deadlines(current_year: int, skills_gap: List[str]) -> List[str]:
    if current_year <= 1:
        base = "before end of 2nd year"
    elif current_year == 2:
        base = "before start of 4th semester break"
    elif current_year == 3:
        base = "before campus season starts"
    else:
        base = "within next 8-12 weeks"

    plans = []
    for idx, skill in enumerate(skills_gap[:6], start=1):
        plans.append(f"{idx}. Build {skill} proficiency {base}")
    if not plans:
        plans.append("1. Focus on interview simulations and resume polish in next 4 weeks")
    return plans


def _recommend_projects(role_targets: List[str]) -> List[str]:
    catalog = {
        "DevOps Engineer": "Deploy a microservice stack on Kubernetes with CI/CD and monitoring",
        "Software Engineer": "Build a full-stack placement prep portal with auth and analytics",
        "Data Scientist": "Create an end-to-end student dropout prediction and dashboard project",
        "Machine Learning Engineer": "Train and serve a resume-job matching model with API",
        "Cybersecurity": "Design a phishing detection browser plugin with risk scoring",
        "Full Stack": "Build a job tracking web app with ATS resume checker integration",
    }
    out = []
    for role in role_targets:
        for key, val in catalog.items():
            if key.lower() in role.lower() and val not in out:
                out.append(val)
    if not out:
        out = [
            "Build a role recommendation engine using your placement dataset",
            "Create a recruiter-style ATS resume checker and explainability dashboard",
        ]
    return out[:4]


def _github_guidance(personal_info: Dict[str, Any], project_count: int) -> List[str]:
    lc = int(_as_float(personal_info.get("leetcodeProblems", 0), 0))
    targets = []
    if lc < 200:
        targets.append(f"Increase LeetCode solved count from {lc} to at least 200")
    if project_count < 3:
        targets.append("Maintain at least 3 production-quality pinned projects on GitHub")
    if not personal_info.get("githubUrl"):
        targets.append("Create and link a complete GitHub profile with README portfolio")
    targets.append("Keep commit activity streak active with meaningful weekly commits")
    return targets


def _resume_quality_check(resume_text: str) -> Dict[str, Any]:
    text = (resume_text or "").strip()
    if not text:
        return {
            "estimatedAtsScore": 55,
            "verdict": "No resume text provided",
            "missing": ["Resume content", "Project impact metrics", "Role-aligned keywords"],
        }

    lowered = text.lower()
    score = 60
    required_sections = ["education", "skills", "projects", "experience"]
    missing = []

    for sec in required_sections:
        if sec in lowered:
            score += 8
        else:
            missing.append(f"Missing section: {sec.title()}")

    has_metrics = bool(re.search(r"\d+%|\d+\+|\d+x", lowered))
    if has_metrics:
        score += 8
    else:
        missing.append("Add measurable impact in bullet points")

    if len(text.split()) < 180:
        score -= 10
        missing.append("Resume is too short for strong ATS confidence")

    score = max(0, min(98, score))
    verdict = "Likely shortlist-ready" if score >= 85 else "Needs improvements before shortlisting"
    return {"estimatedAtsScore": score, "verdict": verdict, "missing": missing}


def _extract_pdf_text_from_base64(pdf_base64: str) -> str:
    if not pdf_base64:
        return ""

    try:
        raw = base64.b64decode(pdf_base64)
        
        # First, try text-based PDF extraction
        reader = PdfReader(io.BytesIO(raw))
        pages = []
        for page in reader.pages:
            page_text = page.extract_text() or ""
            if page_text.strip():
                pages.append(page_text)
        
        extracted_text = "\n".join(pages).strip()
        
        # If text extraction yields content, return it
        if extracted_text and len(extracted_text.split()) > 50:
            return extracted_text
        
        # Fallback: Try OCR on PDF pages (for scanned PDFs) when OCR deps are available.
        if pytesseract is not None and convert_from_bytes is not None:
            try:
                # Check if Tesseract binary is installed and reachable.
                pytesseract.get_tesseract_version()

                images = convert_from_bytes(raw, first_page=1, last_page=3)  # First 3 pages
                ocr_text = []
                for image in images:
                    text = pytesseract.image_to_string(image)
                    if text.strip():
                        ocr_text.append(text)

                if ocr_text:
                    return "\n".join(ocr_text).strip()
            except Exception as ocr_err:
                print(f"OCR not available or failed: {ocr_err}. Continuing without OCR fallback.")
        
        # If still empty, return original extracted text (even if minimal)
        return extracted_text
        
    except Exception as e:
        print(f"PDF extraction error: {e}")
        return ""


def detect_fake_job(job_payload: Dict[str, Any], student_profile: Dict[str, Any] | None = None) -> Dict[str, Any]:
    company = str(job_payload.get("company", "")).strip()
    description = str(job_payload.get("job_description", "")).strip()
    source_url = str(job_payload.get("source_url", "")).strip()
    salary = str(job_payload.get("salary", "")).strip()

    risk_points = 0
    reasons: List[str] = []
    combined = f"{description} {salary}".lower()

    suspicious_markers = [
        "registration fee",
        "pay to apply",
        "telegram",
        "whatsapp only",
        "guaranteed job",
        "no interview",
        "crypto",
    ]
    for marker in suspicious_markers:
        if marker in combined:
            risk_points += 18
            reasons.append(f"Suspicious phrase found: '{marker}'")

    if len(description.split()) < 40:
        risk_points += 15
        reasons.append("Very short/low-detail job description")

    if "%pdf" in combined or "xref" in combined:
        risk_points += 15
        reasons.append("Description appears corrupted or not a real job post")

    if source_url:
        netloc = urlparse(source_url).netloc.lower()
        if company and company.lower() not in netloc and not any(k in netloc for k in ["linkedin", "internshala", "naukri", "indeed", "greenhouse", "lever"]):
            risk_points += 10
            reasons.append("Company name and source URL seem mismatched")
    else:
        risk_points += 8
        reasons.append("Missing source URL")

    risk_points = min(risk_points, 95)
    label = "Likely Fake" if risk_points >= 55 else "Likely Real"

    worth = "Insufficient student data"
    if student_profile:
        p = student_profile.get("personalInfo", student_profile)
        cgpa = _as_float(p.get("currentCGPA", 0))
        skill_strength = sum(
            _as_float(p.get(k, 0))
            for k in ["dsa", "webDev", "mlAi", "dbms", "os", "networking"]
        ) / 6.0
        if cgpa >= 8 and skill_strength >= 3.5:
            worth = "Worth applying now"
        elif cgpa >= 7:
            worth = "Apply selectively; improve skills first"
        else:
            worth = "Not ideal now; prioritize fundamentals and shortlist safer roles"

    return {
        "label": label,
        "riskScore": risk_points,
        "confidence": max(50, 100 - risk_points),
        "reasons": reasons or ["No major fraud signals detected"],
        "worthForStudent": worth,
    }


def _format_user_profile(data: Dict[str, Any]) -> str:
    """Format user profile data into readable text for LLM queries."""
    parts = []
    
    if data.get("name"):
        parts.append(f"Name: {data['name']}")
    
    if data.get("email"):
        parts.append(f"Email: {data['email']}")
    
    if data.get("university"):
        parts.append(f"University: {data['university']}")
    
    if data.get("cgpa"):
        parts.append(f"CGPA: {data['cgpa']}")
    
    if data.get("aim"):
        parts.append(f"Career Goal: {data['aim']}")
    
    if data.get("skills"):
        skills = data['skills']
        if isinstance(skills, dict):
            skill_str = ", ".join([f"{k}: {v}/5" for k, v in skills.items() if v])
            if skill_str:
                parts.append(f"Skills: {skill_str}")
    
    if data.get("projects"):
        parts.append(f"Projects: {data['projects']}")
    
    if data.get("internships"):
        parts.append(f"Internships: {data['internships']}")
    
    if data.get("semesters"):
        parts.append(f"Semester Grades: {data['semesters']}")

    if data.get("subjects"):
        parts.append(f"Subject Scores: {data['subjects']}")
    
    if data.get("resume"):
        parts.append(f"Resume Summary: {data['resume']}")
    
    return "\n".join(parts)


def _normalize_llm_profile(data: Dict[str, Any]) -> Dict[str, Any]:
    """Convert frontend submit payload into a flat LLM profile schema."""
    personal = data.get("personalInfo", data) if isinstance(data, dict) else {}

    skills = {
        "DSA": int(_as_float(personal.get("dsa", 0), 0)),
        "Web": int(_as_float(personal.get("webDev", 0), 0)),
        "ML": int(_as_float(personal.get("mlAi", 0), 0)),
        "DBMS": int(_as_float(personal.get("dbms", 0), 0)),
        "OS": int(_as_float(personal.get("os", 0), 0)),
        "Networking": int(_as_float(personal.get("networking", 0), 0)),
    }

    projects_raw = data.get("projects", []) if isinstance(data, dict) else []
    internships_raw = data.get("internships", []) if isinstance(data, dict) else []
    semesters_raw = data.get("semesters", []) if isinstance(data, dict) else []
    subjects_raw = data.get("subjects", []) if isinstance(data, dict) else []

    project_titles = []
    for item in projects_raw:
        if isinstance(item, dict):
            title = str(item.get("title", "")).strip()
            stack = str(item.get("stack", "")).strip()
            if title and stack:
                project_titles.append(f"{title} ({stack})")
            elif title:
                project_titles.append(title)
        elif str(item).strip():
            project_titles.append(str(item).strip())

    internship_titles = []
    for item in internships_raw:
        if isinstance(item, dict):
            company = str(item.get("company", "")).strip()
            role = str(item.get("role", "")).strip()
            if company and role:
                internship_titles.append(f"{role} at {company}")
            elif company or role:
                internship_titles.append(company or role)
        elif str(item).strip():
            internship_titles.append(str(item).strip())

    semester_scores = []
    for item in semesters_raw:
        if isinstance(item, dict) and str(item.get("sgpa", "")).strip():
            semester_scores.append(str(item.get("sgpa", "")).strip())
        elif str(item).strip():
            semester_scores.append(str(item).strip())

    subject_scores = []
    for item in subjects_raw:
        if isinstance(item, dict):
            subject_name = str(item.get("name", "")).strip()
            marks = str(item.get("marks", "")).strip()
            if subject_name and marks:
                subject_scores.append(f"{subject_name}: {marks}")
            elif subject_name or marks:
                subject_scores.append(subject_name or marks)
        elif str(item).strip():
            subject_scores.append(str(item).strip())

    return {
        "name": personal.get("fullName") or personal.get("name") or "",
        "email": personal.get("email") or "",
        "university": personal.get("collegeName") or personal.get("university") or "",
        "cgpa": personal.get("currentCGPA") or personal.get("cgpa") or "",
        "aim": personal.get("aim") or "",
        "skills": skills,
        "projects": ", ".join(project_titles),
        "internships": ", ".join(internship_titles),
        "semesters": ", ".join(semester_scores),
        "subjects": ", ".join(subject_scores),
        "resume": personal.get("resumeText") or "",
    }


def _truncate_words(text: Any, limit: int) -> str:
    raw = str(text or "")
    words = re.findall(r"\S+", raw)
    if len(words) <= limit:
        return raw.strip()

    tokens = re.findall(r"\S+|\s+", raw)
    out_tokens: List[str] = []
    count = 0
    for token in tokens:
        if token.isspace():
            out_tokens.append(token)
            continue

        count += 1
        if count > limit:
            break
        out_tokens.append(token)

    return "".join(out_tokens).rstrip() + "..."


def analyze_profile(profile: Dict[str, Any]) -> Dict[str, Any]:
    personal = profile.get("personalInfo", {})
    projects = profile.get("projects", [])
    companies = profile.get("companies", [])

    user_cgpa = _as_float(personal.get("currentCGPA", 0))
    user_skills = _extract_user_skills(personal)
    query = _profile_to_query(personal, companies)

    df = load_jobs_df()
    matches = _top_matches(df, query=query, user_skills=user_skills, user_cgpa=user_cgpa)
    top_roles = matches["job_role"].value_counts().head(5).index.tolist()

    required_counter: Dict[str, int] = {}
    for _, row in matches.head(15).iterrows():
        for skill in _parse_skill_list(row.get("required_skills", "")):
            required_counter[skill] = required_counter.get(skill, 0) + 1

    sorted_required = sorted(required_counter.items(), key=lambda x: x[1], reverse=True)
    required_skills = [x[0] for x in sorted_required[:12]]
    skill_gaps = [s for s in required_skills if s not in user_skills][:8]

    target_companies = matches["company_name"].value_counts().head(6).index.tolist()
    deadlines = _generate_deadlines(int(_as_float(personal.get("currentYear", 3), 3)), skill_gaps)
    resume_check = _resume_quality_check(personal.get("resumeText", ""))

    # Build a simple percentage lack metric based on missing top skills.
    lacking_percent = int(min(100, (len(skill_gaps) / max(1, len(required_skills[:8]))) * 100))

    return {
        "hirabilityScore": round(min(99.0, 35 + (user_cgpa * 4.5) + (len(projects) * 4) + (len(user_skills) * 1.5)), 1),
        "recommendedRoles": top_roles,
        "requiredSkillset": required_skills,
        "skillsGap": skill_gaps,
        "whereLacking": {
            "summary": "Gap against top matched requirements",
            "missingSkills": skill_gaps,
            "lackingPercent": lacking_percent,
        },
        "projectRecommendations": _recommend_projects(top_roles),
        "companyTargets": target_companies,
        "salaryExpectationHint": _salary_hint(matches.head(10)),
        "githubChecklist": _github_guidance(personal, len(projects)),
        "strictDeadlines": deadlines,
        "resumeReview": resume_check,
        "matchedJobsPreview": matches[["company_name", "job_role", "domain", "cgpa_requirement", "salary_range", "source_url"]]
        .head(5)
        .to_dict(orient="records"),
    }


@app.route("/api/submit-profile", methods=["POST"])
def submit_profile() -> Tuple[Any, int]:
    try:
        data = request.get_json(silent=True) or {}
        personal = data.get("personalInfo") or {}
        resume_pdf_base64 = data.get("resumePdfBase64", "")
        extracted_resume_text = _extract_pdf_text_from_base64(resume_pdf_base64)
        if extracted_resume_text:
            personal["resumeText"] = extracted_resume_text

        profile = {
            "timestamp": datetime.utcnow().isoformat(),
            "personalInfo": personal,
            "projects": data.get("projects", []),
            "internships": data.get("internships", []),
            "semesters": data.get("semesters", []),
            "subjects": data.get("subjects", []),
            "companies": data.get("companies", []),
            "fakeJobInput": data.get("fakeJobInput", {}),
        }

        analysis = analyze_profile(profile)

        if extracted_resume_text:
            user_context = _format_user_profile(_normalize_llm_profile(data))
            ats_eval = evaluate_resume_ats(extracted_resume_text, user_context)
            analysis["resumeReview"] = {
                "estimatedAtsScore": ats_eval.get("score", 0),
                "grade": ats_eval.get("grade", "C"),
                "verdict": ats_eval.get("verdict", "Needs improvement"),
                "strengths": ats_eval.get("strengths", []),
                "missing": ats_eval.get("improvements", []),
                "source": "uploaded_pdf_ocr",
            }

        fake_input = profile.get("fakeJobInput", {})
        fake_result = detect_fake_job(fake_input, student_profile=profile) if fake_input else None

        llm_output = None
        llm_error = None
        if data.get("enableLlm", True):
            try:
                llm_payload_text = json.dumps(
                    {
                        "personalInfo": personal,
                        "projects": profile.get("projects", []),
                        "internships": profile.get("internships", []),
                        "semesters": profile.get("semesters", []),
                        "companies": profile.get("companies", []),
                        "analysisSnapshot": {
                            "recommendedRoles": analysis.get("recommendedRoles", []),
                            "skillsGap": analysis.get("skillsGap", []),
                            "companyTargets": analysis.get("companyTargets", []),
                        },
                    },
                    ensure_ascii=True,
                )
                llm_output = run_all(llm_payload_text)
            except Exception as exc:
                llm_error = str(exc)

        email_part = _safe_filename_email(personal.get("email", "unknown"))
        filename = PROFILES_DIR / f"{email_part}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "profile": profile,
                    "analysis": analysis,
                    "fakeJobCheck": fake_result,
                    "llm": llm_output,
                    "llmError": llm_error,
                },
                f,
                indent=2,
            )

        return (
            jsonify(
                {
                    "success": True,
                    "message": f"Profile submitted successfully for {personal.get('fullName', 'Student')}",
                    "analysis": analysis,
                    "fakeJobCheck": fake_result,
                    "llm": llm_output,
                    "llmError": llm_error,
                    "profileId": str(filename.name),
                }
            ),
            200,
        )
    except Exception as exc:  # pragma: no cover - defensive API guard
        return jsonify({"error": str(exc)}), 500


@app.route("/api/check-job-reality", methods=["POST"])
def check_job_reality() -> Tuple[Any, int]:
    try:
        payload = request.get_json(silent=True) or {}
        result = detect_fake_job(payload, student_profile=payload.get("student_profile"))
        return jsonify({"success": True, "result": result}), 200
    except Exception as exc:  # pragma: no cover
        return jsonify({"error": str(exc)}), 500


@app.route("/api/refresh-jobs", methods=["POST"])
def refresh_jobs() -> Tuple[Any, int]:
    try:
        payload = request.get_json(silent=True) or {}
        urls = payload.get("urls", [])
        if not urls:
            return jsonify({"error": "Pass urls array in request body"}), 400

        fresh_rows = scrape_jobs_from_urls(urls)
        if not fresh_rows:
            return jsonify({"success": False, "message": "No job rows extracted"}), 200

        fresh_df = pd.DataFrame(fresh_rows)
        existing = pd.read_csv(DATA_PATH) if DATA_PATH.exists() else pd.DataFrame()
        merged = pd.concat([existing, fresh_df], ignore_index=True)
        merged.drop_duplicates(subset=["company_name", "job_role", "source_url"], inplace=True)
        merged.to_csv(DATA_PATH, index=False)

        return jsonify({"success": True, "rowsAdded": len(fresh_rows), "totalRows": len(merged)}), 200
    except Exception as exc:  # pragma: no cover
        return jsonify({"error": str(exc)}), 500


@app.route("/api/profiles", methods=["GET"])
def get_profiles() -> Tuple[Any, int]:
    payload = []
    for file_name in os.listdir(PROFILES_DIR):
        if file_name.endswith(".json"):
            file_path = PROFILES_DIR / file_name
            with open(file_path, "r", encoding="utf-8") as f:
                payload.append(json.load(f))
    return jsonify({"count": len(payload), "profiles": payload}), 200


@app.route("/api/health", methods=["GET"])
def health_check() -> Tuple[Any, int]:
    return jsonify({"status": "ok", "dataset": str(DATA_PATH), "time": datetime.utcnow().isoformat()}), 200


@app.route("/", methods=["GET"])
def serve_index() -> Any:
    html_dir = BASE_DIR / "html"
    return send_from_directory(str(html_dir), "index.html")


@app.route("/<path:filename>", methods=["GET"])
def serve_static_files(filename: str) -> Any:
    html_dir = BASE_DIR / "html"
    file_path = html_dir / filename
    if file_path.exists() and file_path.is_file():
        return send_from_directory(str(html_dir), filename)
    return jsonify({"success": False, "error": "Not found"}), 404


# ============================================================================
# NEW ENDPOINTS FOR 6 SPECIALIZED FEATURES
# ============================================================================


@app.route("/api/dream-cv", methods=["POST"])
def dream_cv() -> Tuple[Any, int]:
    """Generate dream CV for the student."""
    try:
        data = request.get_json() or {}
        user_profile = _format_user_profile(_normalize_llm_profile(data))
        
        from groq_llm_backend import generate_dream_cv
        cv = generate_dream_cv(user_profile)
        
        return jsonify({
            "success": True,
            "dreamCV": cv,
            "message": "Dream CV generated"
        }), 200
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route("/api/github", methods=["POST"])
@app.route("/api/github-recommendations", methods=["POST"])
def github_recommendations() -> Tuple[Any, int]:
    """Generate GitHub strategy recommendations."""
    try:
        data = request.get_json() or {}
        user_profile = _format_user_profile(_normalize_llm_profile(data))
        
        from groq_llm_backend import generate_github_recommendations
        recommendations = generate_github_recommendations(user_profile)
        
        return jsonify({
            "success": True,
            "githubRecommendations": recommendations,
            "message": "GitHub strategy generated"
        }), 200
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route("/api/projects", methods=["POST"])
@app.route("/api/project-suggestions", methods=["POST"])
def project_suggestions() -> Tuple[Any, int]:
    """Generate project suggestions."""
    try:
        data = request.get_json() or {}
        user_profile = _format_user_profile(_normalize_llm_profile(data))
        
        from groq_llm_backend import generate_project_suggestions
        suggestions = generate_project_suggestions(user_profile)
        
        return jsonify({
            "success": True,
            "projectSuggestions": suggestions,
            "message": "Project suggestions generated"
        }), 200
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route("/api/deadlines", methods=["POST"])
@app.route("/api/strict-deadlines", methods=["POST"])
def strict_deadlines() -> Tuple[Any, int]:
    """Generate strict tasks and deadline plan."""
    try:
        data = request.get_json() or {}
        user_profile = _format_user_profile(_normalize_llm_profile(data))
        
        from groq_llm_backend import generate_strict_deadlines_tasks
        plan = generate_strict_deadlines_tasks(user_profile)
        
        return jsonify({
            "success": True,
            "deadlinesPlan": plan,
            "message": "Action plan generated"
        }), 200
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route("/api/mnc-openings", methods=["POST"])
def mnc_openings() -> Tuple[Any, int]:
    """Analyze current openings at top MNCs."""
    try:
        data = request.get_json() or {}
        user_profile = _format_user_profile(_normalize_llm_profile(data))
        
        from groq_llm_backend import generate_current_openings_analysis
        analysis = generate_current_openings_analysis(user_profile)
        
        return jsonify({
            "success": True,
            "mncOpenings": analysis,
            "message": "MNC analysis generated"
        }), 200
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route("/api/topics", methods=["POST"])
@app.route("/api/must-learn-topics", methods=["POST"])
def must_learn_topics() -> Tuple[Any, int]:
    """Generate most important topics to master."""
    try:
        data = request.get_json() or {}
        user_profile = _format_user_profile(_normalize_llm_profile(data))
        
        from groq_llm_backend import generate_must_learn_topics
        topics = generate_must_learn_topics(user_profile)
        
        return jsonify({
            "success": True,
            "mustLearnTopics": topics,
            "message": "Topics generated"
        }), 200
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@app.route("/api/view-resume", methods=["POST"])
def view_resume() -> Tuple[Any, int]:
    """Generate updated resume based on latest data."""
    try:
        data = request.get_json() or {}
        user_profile = _format_user_profile(_normalize_llm_profile(data))
        
        from groq_llm_backend import generate_resume
        resume = generate_resume(user_profile)
        
        return jsonify({
            "success": True,
            "resume": resume,
            "message": "Resume generated"
        }), 200
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


if __name__ == "__main__":
    print("Career Intelligence Backend starting at http://localhost:5000")
    app.run(debug=True, port=5000)
