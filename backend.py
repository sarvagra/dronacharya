"""
Career Profile Evaluation - Python Backend
This is a sample Flask backend that handles form submissions from the frontend.
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import json
from datetime import datetime
import os

app = Flask(__name__)
CORS(app)  # Enable CORS for frontend requests

# Storage directory for submitted profiles
PROFILES_DIR = 'submitted_profiles'
if not os.path.exists(PROFILES_DIR):
    os.makedirs(PROFILES_DIR)


@app.route('/api/submit-profile', methods=['POST'])
def submit_profile():
    """
    Endpoint to receive and process student profile submissions.
    
    Expected JSON structure:
    {
        "personalInfo": {...},
        "projects": [...],
        "internships": [...],
        "semesters": [...],
        "companies": [...]
    }
    """
    try:
        data = request.get_json()
        
        # Validate required fields
        if not data or 'personalInfo' not in data:
            return jsonify({'error': 'Missing personalInfo'}), 400
        
        personal_info = data['personalInfo']
        
        # Extract key information
        full_name = personal_info.get('fullName', 'Unknown')
        email = personal_info.get('email', 'Unknown')
        
        # Create profile record
        profile = {
            'timestamp': datetime.now().isoformat(),
            'personalInfo': personal_info,
            'projects': data.get('projects', []),
            'internships': data.get('internships', []),
            'semesters': data.get('semesters', []),
            'companies': data.get('companies', [])
        }
        
        # Save to file
        filename = f"{PROFILES_DIR}/{email}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(filename, 'w') as f:
            json.dump(profile, f, indent=2)
        
        # Perform analysis (placeholder)
        analysis = analyze_profile(profile)
        
        return jsonify({
            'success': True,
            'message': f'Profile submitted successfully for {full_name}',
            'email': email,
            'analysis': analysis,
            'profileId': filename
        }), 200
        
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/analyze-profile', methods=['POST'])
def analyze_profile_endpoint():
    """
    Additional endpoint for detailed profile analysis.
    """
    try:
        data = request.get_json()
        analysis = analyze_profile(data)
        return jsonify(analysis), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


def analyze_profile(profile):
    """
    Analyze student profile and generate recommendations.
    This is a placeholder - extend with your AI/ML logic.
    """
    personal_info = profile.get('personalInfo', {})
    projects = profile.get('projects', [])
    
    # Calculate hireability score (example logic)
    cgpa = float(personal_info.get('currentCGPA', 0))
    project_count = len(projects)
    skills_avg = calculate_skills_average(personal_info)
    
    hireability_score = calculate_hireability(cgpa, project_count, skills_avg)
    
    analysis = {
        'hirabilityScore': hireability_score,
        'domainFit': personal_info.get('domains', ['General'])[0] if personal_info.get('domains') else 'General',
        'recommendedRoles': generate_role_recommendations(personal_info),
        'strengths': identify_strengths(personal_info),
        'areasForImprovement': identify_improvements(personal_info),
        'nextSteps': generate_next_steps(personal_info)
    }
    
    return analysis


def calculate_hireability(cgpa, projects, skills):
    """Calculate a basic hireability score (0-100)."""
    score = 0
    
    # CGPA component (0-30 points)
    score += min(30, (cgpa / 10) * 30)
    
    # Projects component (0-35 points)
    score += min(35, (projects / 5) * 35)
    
    # Skills component (0-35 points)
    score += min(35, (skills / 5) * 35)
    
    return round(score, 1)


def calculate_skills_average(personal_info):
    """Calculate average of all skills."""
    skills = [
        float(personal_info.get('dsa', 3)),
        float(personal_info.get('webDev', 3)),
        float(personal_info.get('mlAi', 3)),
        float(personal_info.get('dbms', 3)),
        float(personal_info.get('os', 3)),
        float(personal_info.get('networking', 3))
    ]
    return sum(skills) / len(skills)


def generate_role_recommendations(personal_info):
    """Generate role recommendations based on profile."""
    domains = personal_info.get('domains', [])
    roles = {
        'SDE': ['Software Engineer', 'Full Stack Developer', 'Backend Engineer'],
        'AI/ML': ['Machine Learning Engineer', 'AI Researcher', 'Data Scientist'],
        'Data Science': ['Data Scientist', 'Analytics Engineer', 'Business Analyst'],
        'Cybersecurity': ['Security Engineer', 'Penetration Tester', 'Security Analyst'],
        'Full Stack': ['Full Stack Developer', 'Web Developer', 'Frontend Engineer'],
        'DevOps': ['DevOps Engineer', 'Cloud Engineer', 'Infrastructure Engineer']
    }
    
    recommended = []
    for domain in domains:
        if domain in roles:
            recommended.extend(roles[domain])
    
    return list(set(recommended))[:5]  # Return top 5 unique roles


def identify_strengths(personal_info):
    """Identify student strengths."""
    strengths = []
    
    cgpa = float(personal_info.get('currentCGPA', 0))
    if cgpa >= 8.5:
        strengths.append('High CGPA')
    
    for skill in ['dsa', 'webDev', 'mlAi']:
        if float(personal_info.get(skill, 0)) >= 4:
            strengths.append(f'Strong {skill} skills')
    
    if personal_info.get('linkedinUrl'):
        strengths.append('Professional online presence')
    
    return strengths


def identify_improvements(personal_info):
    """Identify areas for improvement."""
    improvements = []
    
    cgpa = float(personal_info.get('currentCGPA', 0))
    if cgpa < 7.0:
        improvements.append(f'Improve academic performance (Current: {cgpa})')
    
    for skill in ['dsa', 'webDev', 'mlAi', 'dbms']:
        if float(personal_info.get(skill, 0)) <= 2:
            improvements.append(f'Build {skill} skills')
    
    if not personal_info.get('githubUrl'):
        improvements.append('Create GitHub portfolio')
    
    return improvements


def generate_next_steps(personal_info):
    """Generate action items for the student."""
    steps = [
        'Complete 100+ LeetCode problems',
        'Build 2-3 real-world projects',
        'Contribute to open-source projects',
        'Network with industry professionals',
        'Prepare for technical interviews'
    ]
    
    return steps


@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({'status': 'Backend is running!'}), 200


@app.route('/api/profiles', methods=['GET'])
def get_all_profiles():
    """Retrieve all submitted profiles (optional admin endpoint)."""
    profiles = []
    for filename in os.listdir(PROFILES_DIR):
        if filename.endswith('.json'):
            with open(os.path.join(PROFILES_DIR, filename), 'r') as f:
                profiles.append(json.load(f))
    return jsonify({'profiles': profiles, 'count': len(profiles)}), 200


if __name__ == '__main__':
    print("🚀 Career Profile Backend Server Starting...")
    print("📍 Running on http://localhost:5000")
    print("📝 API Endpoint: http://localhost:5000/api/submit-profile")
    app.run(debug=True, port=5000)
