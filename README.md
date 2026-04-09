# Dronacharya Career Intelligence Platform

A comprehensive career guidance platform powered by AI and data intelligence. Analyzes student profiles, recommends optimal career paths, detects fraudulent job postings, and generates personalized career reports.

## Features

### Part 1: Student Growth Engine
- **Multi-section student profile form** (personal info, career AIM, skills, projects, internships, university performance, resume)
- **Dataset-grounded recommendations** (role/company matching based on hiring trends)
- **Skill-gap detection** (identifies missing skills and % gap against market requirements)
- **Project recommendations** (tailored to target roles)
- **GitHub acceleration checklist** (actionable milestones)
- **Deadline strategy** (campus hiring season timeline)
- **Resume ATS evaluation** (scores and missing section feedback)
- **Hirability scoring** (overall candidacy assessment)

### Part 2: Job Reality Engine
- **Fake job detection** (AI-powered fraud detection using heuristics and LLM review)
- **Student-profile-aware guidance** (personalized worth assessment)
- **Risk scoring** (confidence level on suspicious indicators)

### Part 3: LLM Career Intelligence
- **Groq-powered career reports** (AI-generated guidance aligned with market trends)
- **ATS-optimized resume generation** (professional formatting + keyword alignment)

## Tech Stack

- **Backend**: Python 3.14 + Flask 3.0.0
- **Frontend**: HTML5 + CSS3 + Vanilla JavaScript
- **LLM**: Groq API (llama-3.3-70b-versatile)
- **Data**: Pandas + CSV datasets (MNC jobs dataset included)
- **Deployment**: Python HTTP server + Flask

## Project Structure

```
├── backend.py                    # Main Flask API server
├── groq_llm_backend.py          # Groq LLM integration (career reports + resume)
├── llm_service_wrapper.py       # LLM service abstraction layer
├── scraper_service.py           # Job scraping utilities
├── html/
│   ├── index.html              # Main frontend
│   ├── style.css               # Frontend styling
│   └── script.js               # Form logic + API integration
├── Data/
│   ├── mnc_jobs_dataset.csv    # Job postings database
│   ├── company_hiring_summary.csv
│   ├── role_hiring_summary.csv
│   ├── job_type_summary.csv
│   └── top_skills_summary.csv
├── requirements.txt             # Python dependencies
├── .env                        # Configuration (Groq API key, etc.)
├── .gitignore                  # Git ignore rules
└── run.sh                      # Deployment startup script
```

## Quick Start

### Automated Deployment (Recommended)

```bash
chmod +x run.sh
./run.sh
```

This will:
- Install dependencies
- Load environment configuration
- Start backend on http://127.0.0.1:5000
- Start frontend on http://127.0.0.1:8000
- Display logs and PIDs

### Manual Setup

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure environment:**
   ```bash
   # Create .env file with:
   GROQ_API_KEY=your_groq_api_key_here
   GROQ_MODEL=llama-3.3-70b-versatile
   ```

3. **Start backend** (Terminal 1):
   ```bash
   python3 backend.py
   ```

4. **Start frontend** (Terminal 2):
   ```bash
   python3 -m http.server 8000 --directory html
   ```

5. **Open in browser:**
   - http://127.0.0.1:8000

## API Endpoints

### Health Check
```
GET /api/health
```
Returns service status and dataset info.

### Submit Profile
```
POST /api/submit-profile
Content-Type: application/json
```

**Request body:**
```json
{
  "name": "Student Name",
  "email": "student@example.com",
  "aim": "Career goal/AIM paragraph",
  "skills": {
    "DSA": 5,
    "Web": 4,
    "ML": 2,
    "DBMS": 4,
    "OS": 3,
    "Networking": 2
  },
  "cgpa": 8.5,
  "projects": "Project descriptions",
  "internships": "Internship experience",
  "semesters": "8.2,8.3,8.4,8.5",
  "university": "University Name",
  "resume": "Resume text or summary"
}
```

**Response includes:**
- Hirability score
- Recommended roles
- Skill gaps
- Company targets
- GitHub checklist
- Project recommendations
- ATS-scored resume review
- LLM-generated career report
- LLM-generated resume

### Check Job Reality
```
POST /api/check-job-reality
Content-Type: application/json
```

**Request body:**
```json
{
  "company_name": "Company Name",
  "job_description": "Job description text",
  "source_url": "https://...",
  "salary_text": "Salary range if available"
}
```

**Response includes:**
- `label`: Genuine or Suspicious
- `riskScore`: 0.0-1.0 confidence
- `confidence`: Confidence percentage
- `reasons`: List of detection factors
- `worthForStudent`: Student-aware assessment

### Refresh Jobs Dataset
```
POST /api/refresh-jobs
Content-Type: application/json
```

**Request body:**
```json
{
  "urls": ["https://example.com/jobs", "https://another.com/careers"]
}
```

## Configuration

### Environment Variables (.env)

```bash
# Groq LLM Configuration (Required)
GROQ_API_KEY=your_groq_api_key
GROQ_MODEL=llama-3.3-70b-versatile

# Optional: Customize base URLs
GROQ_BASE_URL=https://api.groq.com/openai/v1  # Default
```

## Getting Groq API Key

1. Sign up at https://console.groq.com
2. Create an API key
3. Add to `.env` file
4. Free tier includes:
   - 30 requests/minute
   - Full access to all models
   - No billing required to start

## Data & Models

**LLM Model:** Llama 3.3 70B Versatile
- 70 billion parameters
- Excellent reasoning and instruction following
- Optimized for rapid inference (Groq)

**Dataset:** MNC Jobs Database
- ~4000+ job postings
- 50+ companies
- 100+ job roles
- Salary ranges and CGPA requirements
- Hiring trends analysis

## Logs

- **Backend logs:** `backend.log`
- **Frontend access:** Console (browser DevTools)
- **View logs in terminal:** `tail -f backend.log`

## Stopping Services

```bash
# If using run.sh (note the PIDs printed)
kill <BACKEND_PID> <FRONTEND_PID>

# Or find and kill by port
lsof -ti:5000 | xargs kill -9  # Backend
lsof -ti:8000 | xargs kill -9  # Frontend
```

## Response Format Examples

### Success Response
```json
{
  "success": true,
  "message": "Profile submitted successfully",
  "analysis": {
    "hirabilityScore": 95.5,
    "recommendedRoles": ["Software Engineer", "Backend Developer"],
    "skillsGap": ["Docker", "Kubernetes"],
    "companyTargets": ["Google", "Microsoft", "Amazon"],
    "projectRecommendations": ["Build microservices", "Deploy to cloud"],
    "resumeReview": {
      "estimatedAtsScore": 88,
      "missing": ["Quantified achievements", "Metrics"],
      "verdict": "Strong, but needs metrics"
    },
    "githubChecklist": ["Contribute to OSS", "200 LeetCode problems"],
    "strictDeadlines": ["1. Build Docker skills by Month 2", "2. Deploy 2 cloud projects by Month 3"]
  },
  "llm": {
    "careerReport": "Software Engineer (primary), DevOps Engineer (secondary)...",
    "resumeText": "**John Doe**\nEducation: IIT Bombay, CGPA: 8.5..."
  }
}
```

## Performance Notes

- **Response time:** 2-5 seconds (includes LLM generation)
- **Concurrent users:** Up to 5-10 on single instance
- **Scalability:** Use WSGI server (Gunicorn) for production

## Production Deployment

For production use:

1. **Use Gunicorn WSGI server:**
   ```bash
   pip install gunicorn
   gunicorn -w 4 -b 127.0.0.1:5000 backend:app
   ```

2. **Use nginx reverse proxy:**
   ```nginx
   upstream backend {
     server 127.0.0.1:5000;
   }
   server {
     listen 80;
     location / { proxy_pass http://backend; }
     location /api { proxy_pass http://backend; }
   }
   ```

3. **Load balancing:** Deploy multiple backend instances behind nginx

4. **SSL/TLS:** Use Let's Encrypt for HTTPS

## Troubleshooting

### Backend won't start
```bash
# Check if port 5000 is in use
lsof -i :5000
kill -9 <PID>

# Run with debug output
python3 backend.py
```

### Frontend blank page
- Clear browser cache (Ctrl+Shift+Delete or Cmd+Shift+Delete)
- Check browser console for errors (F12)
- Verify frontend server is running on :8000

### LLM not generating output
- Verify Groq API key in `.env`
- Check Groq quota at https://console.groq.com
- Look for errors in `backend.log`

### CORS errors
- Already handled with `flask-cors`
- If issues persist, verify backend is running on :5000

## Contributing

For contributions:
1. Create feature branch
2. Test all endpoints
3. Update documentation
4. Submit pull request

## License

This project is provided as-is for educational and commercial use.

## Support

For issues or questions:
1. Check logs: `tail -f backend.log`
2. Verify `.env` configuration
3. Test API endpoints with curl
4. Check Groq API status at https://status.groq.com


4. Open:

- Frontend: http://localhost:8000/html/index.html
- Backend health: http://localhost:5000/api/health

## Main API Endpoints

- POST /api/submit-profile
  - Full end-to-end profile analysis
- POST /api/check-job-reality
  - Standalone fake-job check
- POST /api/refresh-jobs
  - Scrape URLs and append rows in dataset
- GET /api/profiles
  - Saved submissions and analyses
- GET /api/health
  - Health check

## Sample Submit Payload

```json
{
  "personalInfo": {
    "fullName": "Aarav Singh",
    "email": "aarav@example.com",
    "phone": "9999999999",
    "collegeName": "NIT Delhi",
    "degree": "BTech",
    "branch": "CSE",
    "currentYear": "3",
    "currentCGPA": "8.1",
    "aim": "I want an SDE or ML role in top product companies.",
    "domains": ["SDE", "AI/ML"],
    "dsa": "4",
    "webDev": "3",
    "mlAi": "4",
    "dbms": "3",
    "os": "3",
    "networking": "3",
    "leetcodeProblems": "180",
    "resumeText": "Education Skills Projects Experience ..."
  },
  "projects": [
    {
      "title": "Placement Predictor",
      "domain": "AI/ML",
      "stack": "Python, Flask"
    }
  ],
  "internships": [],
  "semesters": [
    {
      "sgpa": "8.3"
    }
  ],
  "companies": ["Google", "Microsoft"],
  "fakeJobInput": {
    "company": "Google",
    "job_description": "Hiring SDE intern. Strong DSA and system design basics required.",
    "source_url": "https://careers.google.com/jobs/results/",
    "salary": "12 LPA"
  }
}
```

## Notes

- The fake-job detector uses explainable heuristics (risk phrases, metadata quality, source mismatch, malformed descriptions).
- Gemini-powered generation requires GEMINI_API_KEY (or GOOGLE_API_KEY) in environment.
- Dataset quality affects recommendation quality; use /api/refresh-jobs to keep data updated.
