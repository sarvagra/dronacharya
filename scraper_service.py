"""Best-effort job scraping utilities used by backend refresh endpoint."""

from __future__ import annotations

from datetime import date
from typing import Any, Dict, List
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup


def _guess_source(netloc: str) -> str:
    netloc = netloc.lower()
    if "linkedin" in netloc:
        return "linkedin"
    if "internshala" in netloc:
        return "internshala"
    if "naukri" in netloc:
        return "naukri"
    if "indeed" in netloc:
        return "indeed"
    return "careers_page"


def _extract_text(soup: BeautifulSoup, selectors: List[str], fallback: str = "") -> str:
    for selector in selectors:
        node = soup.select_one(selector)
        if node:
            text = node.get_text(" ", strip=True)
            if text:
                return text
    return fallback


def scrape_jobs_from_urls(urls: List[str], timeout: int = 20) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []

    for url in urls:
        try:
            response = requests.get(url, timeout=timeout, headers={"User-Agent": "Mozilla/5.0"})
            if response.status_code != 200:
                continue

            soup = BeautifulSoup(response.text, "html.parser")
            title = _extract_text(soup, ["h1", "title"], fallback="Unknown Role")
            description = _extract_text(
                soup,
                [
                    "article",
                    "main",
                    ".job-description",
                    "[class*='description']",
                    "[id*='description']",
                ],
                fallback="",
            )
            domain = _extract_text(soup, ["meta[name='keywords']"], fallback="General")
            if not isinstance(domain, str) or not domain:
                domain = "General"

            host = urlparse(url).netloc
            company = host.split(".")[0].replace("www", "").replace("careers", "").strip("-")
            company = company.title() if company else "Unknown"

            row = {
                "company_name": company,
                "industry/domain": "General",
                "job_role": title[:80],
                "job_title_raw": title[:120],
                "job_type": "Not specified",
                "required_skills": "[]",
                "preferred_skills": "[]",
                "cgpa_requirement": "Not specified",
                "experience_required": "Not specified",
                "job_description": description[:4000],
                "location": "Not specified",
                "salary_range": "Not specified",
                "source": _guess_source(host),
                "date_posted": str(date.today()),
                "source_url": url,
            }
            rows.append(row)
        except Exception:
            continue

    return rows
