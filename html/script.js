const API_BASE_URL = (() => {
    const host = window.location.hostname || "127.0.0.1";
    return `http://${host}:5000/api`;
})();

let currentStep = 1;
const totalSteps = 6;
const formData = {};
const projects = [];
const internships = [];
const semesters = [];
const subjects = [];
let companies = [];
let lastProfileData = {}; // Store last submitted profile for action buttons
const LAST_PROFILE_KEY = "lastSubmittedProfile";
const SUBMITTED_STATE_KEY = "profileSubmitted";
let isSubmitting = false;
let lastAtsScore = 0;

function toUserFriendlyError(error) {
    const raw = String(error?.message || error || "Unknown error");
    const lower = raw.toLowerCase();
    if (lower.includes("failed to fetch") || lower.includes("networkerror")) {
        return `Could not reach backend at ${API_BASE_URL}. Ensure backend is running on port 5000 and open frontend via http://127.0.0.1:8000/index.html`;
    }
    return raw;
}

document.addEventListener("DOMContentLoaded", () => {
    loadFormData();
    attachEventListeners();
    initializeStepNavigation();
    loadTheme();
    restoreResults();
    const submitted = sessionStorage.getItem(SUBMITTED_STATE_KEY) === "1";
    if (!submitted) {
        showStep(1);
    }
});

function loadTheme() {
    if (localStorage.getItem("theme") === "dark") {
        document.body.classList.add("dark-mode");
    }
    updateThemeToggle();
}

function updateThemeToggle() {
    document.getElementById("themeToggle").textContent = document.body.classList.contains("dark-mode") ? "Light" : "Dark";
}

function saveFormData() {
    const form = document.getElementById("mainForm");
    const local = {};

    Array.from(form.elements).forEach((el) => {
        if (!el.name) return;
        if (el.type === "checkbox") {
            if (["domains", "cloudPlatforms"].includes(el.name)) {
                if (!local[el.name]) local[el.name] = [];
                if (el.checked) local[el.name].push(el.value);
            } else {
                local[el.name] = el.checked;
            }
            return;
        }

        if (el.type !== "file") {
            local[el.name] = el.value;
        }
    });

    Object.keys(formData).forEach((k) => delete formData[k]);
    Object.assign(formData, local);
    localStorage.setItem("careerFormData", JSON.stringify(formData));
}

function loadFormData() {
    const saved = localStorage.getItem("careerFormData");
    if (!saved) return;
    Object.assign(formData, JSON.parse(saved));
    loadFormToUI();
}

function loadFormToUI() {
    Object.keys(formData).forEach((name) => {
        const value = formData[name];
        const nodes = document.querySelectorAll(`[name="${name}"]`);
        if (!nodes.length) return;

        nodes.forEach((node) => {
            if (node.type === "checkbox") {
                if (Array.isArray(value)) {
                    node.checked = value.includes(node.value);
                } else {
                    node.checked = Boolean(value);
                }
            } else if (node.type !== "file") {
                node.value = value;
            }
        });
    });

    if (Array.isArray(formData.domains)) {
        formData.domains.forEach((domain) => {
            const box = document.querySelector(`input[name="domains"][value="${domain}"]`);
            if (box) box.checked = true;
        });
    }
}

function attachEventListeners() {
    const form = document.getElementById("mainForm");
    form.addEventListener("submit", (e) => {
        e.preventDefault();
        e.stopPropagation();
        if (currentStep === totalSteps) {
            submitForm();
        }
    });

    form.addEventListener("keydown", (e) => {
        if (e.key === "Enter" && e.target && e.target.tagName !== "TEXTAREA") {
            e.preventDefault();
        }
    });

    document.getElementById("themeToggle").addEventListener("click", () => {
        document.body.classList.toggle("dark-mode");
        localStorage.setItem("theme", document.body.classList.contains("dark-mode") ? "dark" : "light");
        updateThemeToggle();
    });

    document.getElementById("backlogs").addEventListener("change", (e) => {
        const count = document.getElementById("backlogsCount");
        const label = document.getElementById("backlogsLabel");
        count.style.display = e.target.checked ? "block" : "none";
        label.textContent = e.target.checked ? "Yes" : "No";
    });

    const salaryNode = document.querySelector('[name="expectedSalary"]');
    if (salaryNode) {
        salaryNode.addEventListener("input", (e) => {
            document.getElementById("salaryValue").textContent = e.target.value;
        });
    }

    document.querySelectorAll(".skill-slider").forEach((slider) => {
        slider.addEventListener("input", (e) => {
            const output = document.getElementById(`${e.target.name}Value`);
            if (output) output.textContent = e.target.value;
        });
    });

    const aimNode = document.querySelector('[name="aim"]');
    if (aimNode) {
        aimNode.addEventListener("input", (e) => {
            const chars = e.target.value.length;
            document.getElementById("aimCount").textContent = String(chars);
        });
    }

    document.getElementById("companiesInput").addEventListener("keypress", (e) => {
        if (e.key === "Enter" && e.target.value.trim()) {
            e.preventDefault();
            companies.push(e.target.value.trim());
            renderCompanyTags();
            e.target.value = "";
        }
    });

    document.getElementById("addProjectBtn").addEventListener("click", addProject);
    document.getElementById("addInternshipBtn").addEventListener("click", addInternship);
    document.getElementById("addSemesterBtn").addEventListener("click", addSemester);
    document.getElementById("addSubjectBtn").addEventListener("click", addSubject);

    document.getElementById("resumeUpload").addEventListener("change", (e) => {
        const info = document.getElementById("resumeFileName");
        info.textContent = e.target.files.length ? `Uploaded: ${e.target.files[0].name}` : "";
    });

    document.getElementById("prevBtn").addEventListener("click", () => {
        if (currentStep > 1) showStep(currentStep - 1);
    });

    document.getElementById("nextBtn").addEventListener("click", (e) => {
        e.preventDefault();
        e.stopPropagation();
        if (currentStep < totalSteps) {
            showStep(currentStep + 1);
        } else {
            submitForm();
        }
    });

    // Add event listeners for action buttons
    document.querySelectorAll(".action-btn").forEach((btn) => {
        btn.addEventListener("click", (e) => {
            e.preventDefault();
            e.stopPropagation();
            const action = btn.getAttribute("data-action");
            handleActionButton(action);
        });
    });
}

function initializeStepNavigation() {
    document.querySelectorAll(".step-item").forEach((item) => {
        item.addEventListener("click", () => {
            const step = parseInt(item.dataset.step, 10);
            if (!Number.isNaN(step)) showStep(step);
        });
    });
}

function showStep(step) {
    saveFormData();
    document.querySelectorAll(".form-step").forEach((n) => n.classList.remove("active"));
    document.querySelectorAll(".step-item").forEach((n) => n.classList.remove("active"));

    const stepNode = document.querySelector(`.form-step[data-step="${step}"]`);
    const itemNode = document.querySelector(`.step-item[data-step="${step}"]`);
    if (!stepNode || !itemNode) return;

    stepNode.classList.add("active");
    itemNode.classList.add("active");

    document.getElementById("progressBarInner").style.width = `${(step / totalSteps) * 100}%`;
    document.getElementById("prevBtn").style.display = step === 1 ? "none" : "flex";
    document.getElementById("nextBtn").textContent = step === totalSteps ? "Submit and Analyze" : "Next →";

    currentStep = step;
    window.scrollTo({ top: 0, behavior: "smooth" });
}

function addProject() {
    projects.push({ id: crypto.randomUUID() });
    renderProjects();
}

function removeProject(index) {
    projects.splice(index, 1);
    renderProjects();
}

function renderProjects() {
    const list = document.getElementById("projectsList");
    list.innerHTML = "";

    projects.forEach((_, index) => {
        const card = document.createElement("div");
        card.className = "project-card";
        card.innerHTML = `
            <div class="project-card-header">
                <strong>Project ${index + 1}</strong>
                <button type="button" class="btn btn-danger btn-small" onclick="removeProject(${index})">Delete</button>
            </div>
            <div class="form-row">
                <div class="form-group">
                    <label>Project Title</label>
                    <input type="text" data-key="title" placeholder="Career dashboard project">
                </div>
                <div class="form-group">
                    <label>Domain</label>
                    <input type="text" data-key="domain" placeholder="AI/ML, SDE, Cybersecurity">
                </div>
            </div>
            <div class="form-group">
                <label>Tech Stack</label>
                <input type="text" data-key="stack" placeholder="Flask, React, PostgreSQL">
            </div>
            <div class="form-group">
                <label>Description</label>
                <textarea data-key="description" placeholder="Impact-oriented summary"></textarea>
            </div>
            <div class="form-group">
                <label>GitHub Link</label>
                <input type="url" data-key="github" placeholder="https://github.com/user/repo">
            </div>
        `;
        list.appendChild(card);
    });
}

function addInternship() {
    internships.push({ id: crypto.randomUUID() });
    renderInternships();
}

function removeInternship(index) {
    internships.splice(index, 1);
    renderInternships();
}

function renderInternships() {
    const list = document.getElementById("internshipsList");
    list.innerHTML = "";

    internships.forEach((_, index) => {
        const card = document.createElement("div");
        card.className = "project-card";
        card.innerHTML = `
            <div class="project-card-header">
                <strong>Internship ${index + 1}</strong>
                <button type="button" class="btn btn-danger btn-small" onclick="removeInternship(${index})">Delete</button>
            </div>
            <div class="form-row">
                <div class="form-group">
                    <label>Company</label>
                    <input type="text" data-key="company" placeholder="Company name">
                </div>
                <div class="form-group">
                    <label>Role</label>
                    <input type="text" data-key="role" placeholder="Intern role">
                </div>
            </div>
            <div class="form-group">
                <label>Duration</label>
                <input type="text" data-key="duration" placeholder="3 months">
            </div>
        `;
        list.appendChild(card);
    });
}

function addSemester() {
    semesters.push({ id: crypto.randomUUID() });
    renderSemesters();
}

function removeSemester(index) {
    semesters.splice(index, 1);
    renderSemesters();
}

function renderSemesters() {
    const list = document.getElementById("semestersList");
    list.innerHTML = "";

    semesters.forEach((_, index) => {
        const card = document.createElement("div");
        card.className = "project-card";
        card.innerHTML = `
            <div class="project-card-header">
                <strong>Semester ${index + 1}</strong>
                <button type="button" class="btn btn-danger btn-small" onclick="removeSemester(${index})">Delete</button>
            </div>
            <div class="form-group">
                <label>SGPA</label>
                <input type="number" min="0" max="10" step="0.01" data-key="sgpa" placeholder="8.4">
            </div>
        `;
        list.appendChild(card);
    });
}

function addSubject() {
    subjects.push({ id: crypto.randomUUID() });
    renderSubjects();
}

function removeSubject(index) {
    subjects.splice(index, 1);
    renderSubjects();
}

function renderSubjects() {
    const list = document.getElementById("subjectsList");
    list.innerHTML = "";

    subjects.forEach((_, index) => {
        const card = document.createElement("div");
        card.className = "project-card";
        card.innerHTML = `
            <div class="project-card-header">
                <strong>Subject ${index + 1}</strong>
                <button type="button" class="btn btn-danger btn-small" onclick="removeSubject(${index})">Delete</button>
            </div>
            <div class="form-row">
                <div class="form-group">
                    <label>Subject Name</label>
                    <input type="text" data-key="name" placeholder="e.g. Compiler Design">
                </div>
                <div class="form-group">
                    <label>Marks / Grade</label>
                    <input type="text" data-key="marks" placeholder="e.g. 86 or A-">
                </div>
            </div>
        `;
        list.appendChild(card);
    });
}

function renderCompanyTags() {
    const container = document.getElementById("companiesTags");
    const input = document.getElementById("companiesInput");
    container.innerHTML = "";

    companies.forEach((company, index) => {
        const tag = document.createElement("div");
        tag.className = "tag";
        tag.innerHTML = `${company}<span class="tag-remove" onclick="removeCompany(${index})">x</span>`;
        container.appendChild(tag);
    });
    container.appendChild(input);
}

function removeCompany(index) {
    companies.splice(index, 1);
    renderCompanyTags();
}

function collectSectionData(containerId) {
    const cards = Array.from(document.querySelectorAll(`#${containerId} .project-card`));
    return cards.map((card) => {
        const item = {};
        card.querySelectorAll("[data-key]").forEach((node) => {
            item[node.dataset.key] = node.value;
        });
        return item;
    });
}

function validateForm() {
    saveFormData();
    return true;
}

async function submitForm() {
    if (isSubmitting) return;
    if (!validateForm()) {
        showNotification("Fill all required fields first", "error");
        return;
    }

    isSubmitting = true;

    const submitBtn = document.getElementById("nextBtn");
    const previous = submitBtn.textContent;
    submitBtn.innerHTML = '<span class="loading"></span> Processing';
    submitBtn.disabled = true;

    try {
        const resumePdfBase64 = await getResumePdfBase64();
        const payload = {
            personalInfo: { ...formData },
            projects: collectSectionData("projectsList"),
            internships: collectSectionData("internshipsList"),
            semesters: collectSectionData("semestersList"),
            subjects: collectSectionData("subjectsList"),
            companies,
            resumePdfBase64,
        };

        const response = await fetch(`${API_BASE_URL}/submit-profile`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
        });
        const result = await response.json();

        if (!response.ok) {
            throw new Error(result.error || "Submit failed");
        }

        // Store the profile data for action buttons
        lastProfileData = payload;
        localStorage.setItem(LAST_PROFILE_KEY, JSON.stringify(payload));
        renderResults(result);
        sessionStorage.setItem(SUBMITTED_STATE_KEY, "1");
        setSubmittedView(true);
        showActionButtons();
        await handleActionButton("dream-cv");
        showNotification("Profile analysis complete", "success");
    } catch (error) {
        console.error(error);
        showNotification(toUserFriendlyError(error), "error");
    } finally {
        submitBtn.textContent = previous;
        submitBtn.disabled = false;
        isSubmitting = false;
    }
}

function renderResults(result) {
    const container = document.getElementById("resultContainer");
    const review = result?.analysis?.resumeReview || {};
    const score = review.estimatedAtsScore ?? "N/A";
    lastAtsScore = typeof score === "number" ? score : 0;
    const grade = review.grade || (typeof score === "number" ? (score >= 85 ? "A" : (score >= 70 ? "B" : "C")) : "N/A");
    const verdict = review.verdict || "ATS review generated from uploaded resume.";

    container.innerHTML = `
        <div class="result-card">
            <h3>📊 Resume ATS Review</h3>
            <div class="tile-grid">
                <div class="mini-tile">
                    <div class="mini-tile-title">ATS Score</div>
                    <div class="mini-tile-body">${escapeHtml(String(score))}</div>
                </div>
                <div class="mini-tile">
                    <div class="mini-tile-title">Grade</div>
                    <div class="mini-tile-body">${escapeHtml(String(grade))}</div>
                </div>
                <div class="mini-tile">
                    <div class="mini-tile-title">Verdict</div>
                    <div class="mini-tile-body">${escapeHtml(String(verdict))}</div>
                </div>
            </div>
        </div>
    `;
    container.style.display = "grid";
    localStorage.setItem("lastAnalysisResult", JSON.stringify(result));
}

async function checkJobReality() {
    try {
        const payload = {
            company: document.getElementById("jobCompany").value,
            job_description: document.getElementById("jobDescription").value,
            source_url: document.getElementById("jobSourceUrl").value,
            salary: document.getElementById("jobSalary").value,
            student_profile: { personalInfo: formData },
        };

        const response = await fetch(`${API_BASE_URL}/check-job-reality`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
        });
        const data = await response.json();
        if (!response.ok) throw new Error(data.error || "Could not check job reality");

        const target = document.getElementById("jobCheckResult");
        target.innerHTML = `<strong>${data.result.label}</strong> | Risk ${data.result.riskScore} | ${data.result.worthForStudent}`;
        target.style.display = "block";
        localStorage.setItem("lastJobRealityResult", target.innerHTML);
    } catch (error) {
        showNotification(error.message, "error");
    }
}

function restoreResults() {
    const lastProfileRaw = localStorage.getItem(LAST_PROFILE_KEY);
    if (lastProfileRaw) {
        try {
            lastProfileData = JSON.parse(lastProfileRaw);
        } catch (_err) {
            localStorage.removeItem(LAST_PROFILE_KEY);
            lastProfileData = {};
        }
    }

    const submitted = sessionStorage.getItem(SUBMITTED_STATE_KEY) === "1";
    if (submitted && lastProfileData && lastProfileData.personalInfo) {
        setSubmittedView(true);
        showActionButtons();
        const container = document.getElementById("resultContainer");
        if (container && !container.innerHTML.trim()) {
            handleActionButton("dream-cv");
        }
    } else {
        setSubmittedView(false);
    }

    const lastJobReality = localStorage.getItem("lastJobRealityResult");
    if (lastJobReality) {
        const target = document.getElementById("jobCheckResult");
        if (target) {
            target.innerHTML = lastJobReality;
            target.style.display = "block";
        }
    }
}

async function getResumePdfBase64() {
    const upload = document.getElementById("resumeUpload");
    if (!upload || !upload.files || !upload.files.length) return "";

    const file = upload.files[0];
    if (!file || file.type !== "application/pdf") return "";

    return await new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => {
            const raw = String(reader.result || "");
            const commaIndex = raw.indexOf(",");
            resolve(commaIndex >= 0 ? raw.slice(commaIndex + 1) : raw);
        };
        reader.onerror = () => reject(new Error("Could not read resume PDF"));
        reader.readAsDataURL(file);
    });
}

function showNotification(message, type = "info", timeoutMs = 0) {
    const notification = document.createElement("div");
    notification.className = type === "error" ? "error-message" : "success-message";
    notification.innerHTML = `<span>${message}</span> <button type="button" style="margin-left:8px;border:none;background:transparent;cursor:pointer;font-weight:700;">x</button>`;
    notification.style.position = "fixed";
    notification.style.top = "20px";
    notification.style.right = "20px";
    notification.style.zIndex = "9999";
    notification.style.maxWidth = "340px";
    notification.style.display = "flex";
    notification.style.alignItems = "center";
    notification.style.gap = "6px";

    document.body.appendChild(notification);

    const closeBtn = notification.querySelector("button");
    if (closeBtn) {
        closeBtn.addEventListener("click", () => notification.remove());
    }

    if (timeoutMs > 0) {
        setTimeout(() => notification.remove(), timeoutMs);
    }
}

document.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && e.ctrlKey) {
        submitForm();
    }
    if (e.key === "ArrowRight" && currentStep < totalSteps) {
        showStep(currentStep + 1);
    }
    if (e.key === "ArrowLeft" && currentStep > 1) {
        showStep(currentStep - 1);
    }
});

// ============================================================================
// ACTION BUTTON FUNCTIONS (6 Specialized Features)
// ============================================================================

function showActionButtons() {
    const actionHub = document.getElementById("sidebarActionButtons");
    if (!actionHub) return;
    actionHub.style.display = "block";
}

function setSubmittedView(isSubmitted) {
    const form = document.getElementById("mainForm");
    const progressBar = document.querySelector(".progress-bar");
    const steps = document.querySelector(".steps");
    const actionHub = document.getElementById("sidebarActionButtons");

    if (form) {
        form.style.display = isSubmitted ? "none" : "block";
    }
    if (progressBar) {
        progressBar.style.display = isSubmitted ? "none" : "block";
    }
    if (steps) {
        steps.style.display = isSubmitted ? "none" : "flex";
    }
    if (actionHub) {
        actionHub.style.display = isSubmitted ? "block" : "none";
    }
}

async function handleActionButton(action) {
    if (!lastProfileData || !lastProfileData.personalInfo) {
        showNotification("Please fill and submit the form first", "error");
        return;
    }

    const resultContainer = document.getElementById("resultContainer");
    const endpointMap = {
        "dream-cv": "dream-cv",
        "github": "github-recommendations",
        "projects": "project-suggestions",
        "deadlines": "strict-deadlines",
        "mnc-openings": "mnc-openings",
        "topics": "must-learn-topics",
    };

    const actionTitles = {
        "dream-cv": "📄 Dream CV - Your Ideal Profile",
        "github": "🐙 GitHub Strategy Recommendations",
        "projects": "💼 Portfolio Projects Suggestions",
        "deadlines": "⏰ Strict Action Plan & Deadlines",
        "mnc-openings": "🏢 Top MNC Job Analysis",
        "topics": "🎯 Must-Learn Topics for MNCs",
    };

    try {
        const endpoint = endpointMap[action];
        if (!endpoint) {
            throw new Error("Unsupported action requested");
        }

        // Show result container when clicking action buttons
        resultContainer.style.display = "grid";
        // Show only one result tile at a time
        resultContainer.innerHTML = "";

        const actionButtons = document.querySelectorAll(".action-btn");
        actionButtons.forEach((button) => {
            button.disabled = true;
        });

        // Show loading state
        let resultCard = document.createElement("div");
        resultCard.className = "result-card";
        resultCard.innerHTML = `<h3>${actionTitles[action] || "Loading..."}</h3><p style="color: #666; font-style: italic;">⏳ Generating personalized recommendations...</p>`;
        resultContainer.appendChild(resultCard);

        const response = await fetch(`${API_BASE_URL}/${endpoint}`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(lastProfileData),
        });

        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.error || "Failed to generate recommendations");
        }
        let content = "";

        switch (action) {
            case "dream-cv":
                content = data.dreamCV || data.data || "No data received";
                break;
            case "github":
                content = data.githubRecommendations || data.data ||  "No recommendations available";
                break;
            case "projects":
                content = data.projectSuggestions || data.data || "No projects suggested";
                break;
            case "deadlines":
                content = data.deadlinesPlan || data.data || "No plan available";
                break;
            case "mnc-openings":
                content = data.mncOpenings || data.data || "No analysis available";
                break;
            case "topics":
                content = data.mustLearnTopics || data.data || "No topics available";
                break;
        }

        content = formatActionOutput(content, action);
        const contentHtml = renderActionContent(content, action);
        const actionButtonsHtml = getActionSpecificButtons(action);

        // Update the card with actual content
        resultCard.innerHTML = `
            <h3>${actionTitles[action]}</h3>
            <div class="output-content output-content--${action}">
                ${contentHtml}
            </div>
            ${actionButtonsHtml}
        `;

        resultContainer.scrollIntoView({ behavior: "smooth", block: "start" });
        showNotification("Recommendations generated successfully", "success");
    } catch (error) {
        console.error(error);
        showNotification(`Error: ${toUserFriendlyError(error)}`, "error");
    } finally {
        document.querySelectorAll(".action-btn").forEach((button) => {
            button.disabled = false;
        });
    }
}

function escapeHtml(text) {
    const map = {
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#039;",
    };
    return String(text).replace(/[&<>"']/g, (m) => map[m]);
}

function copyToClipboard(btn) {
    const text = btn.parentElement.querySelector("div").innerText;
    navigator.clipboard.writeText(text).then(() => {
        showNotification("Copied to clipboard!", "success");
        const original = btn.textContent;
        btn.textContent = "✅ Copied!";
        setTimeout(() => {
            btn.textContent = original;
        }, 2000);
    }).catch(() => showNotification("Failed to copy", "error"));
}

function stripMarkdown(text) {
    return String(text || "")
        .replace(/\r\n/g, "\n")
        .replace(/^#{1,6}\s+/gm, "")
        .replace(/^>\s?/gm, "")
        .replace(/\*\*(.*?)\*\*/g, "$1")
        .replace(/__(.*?)__/g, "$1")
        .replace(/`{1,3}([^`]+)`{1,3}/g, "$1")
        .replace(/\[(.*?)\]\((.*?)\)/g, "$1 ($2)")
        .replace(/^\s*[-*]\s+/gm, "• ")
        .replace(/\s\*\s+/g, "\n• ")
        .replace(/\s•\s+/g, "\n• ")
        .replace(/\*\s+/g, "• ")
        .replace(/\n{3,}/g, "\n\n")
        .trim();
}

function formatActionOutput(rawText, action) {
    const noMarkdown = stripMarkdown(rawText);
    return noMarkdown;
}

function splitChunks(text) {
    return String(text || "")
        .split(/\n\s*\n|\n(?=• )/)
        .map((chunk) => chunk.trim())
        .filter(Boolean);
}

function chunkLines(text) {
    return String(text || "")
        .split(/\n+/)
        .map((line) => line.trim())
        .filter(Boolean);
}

function renderActionContent(text, action) {
    switch (action) {
        case "dream-cv":
            return renderResumeSheet(text);
        case "github":
            return renderStructuredSections(text, "GitHub Recommendations");
        case "projects":
            return renderStructuredSections(text, "Project Suggestions");
        case "deadlines":
            return renderStructuredSections(text, "Strict Action Plan & Deadlines", { sectionPrefix: "Step" });
        case "mnc-openings":
            return renderStructuredSections(text, "Top MNC Job Analysis", { sectionPrefix: "Company" });
        case "topics":
            return renderStructuredSections(text, "Must-Learn Topics", { sectionPrefix: "Topic" });
        default:
            return `<div class="output-fallback">${escapeHtml(text)}</div>`;
    }
}

function renderStructuredSections(text, fallbackHeading, options = {}) {
    const sectionPrefix = options.sectionPrefix || "Section";
    const raw = String(text || "")
        .replace(/\r/g, "\n")
        .replace(/\t/g, " ")
        .replace(/\u00a0/g, " ")
        .trim();

    if (!raw) {
        return `<p class="output-paragraph">No ${escapeHtml(fallbackHeading.toLowerCase())} available.</p>`;
    }

    const prepared = raw
        .replace(/\s+(?=\d+\.\s+[A-Z*])/g, "\n")
        .replace(/\s+(?=(?:Project|Company|Topic|Step|Week|Phase|Action)\s+\d+\s*:)/gi, "\n")
        .replace(/\s+(?=(?:Why|Resources|Expected learning time|Demonstrate mastery|Real-world application|Description|Tech Stack|Timeline|Expected Impact|CGPA match|Matching roles|Skill gaps|Pathway|Actionability rating|Current Skills|Platforms\/Resources|Official Certifications to Pursue|6-Month Plan|Week-by-Week Tasks)\s*:)/gi, "\n")
        .replace(/\s([•+\-*])\s/g, "\n$1 ")
        .replace(/\n{3,}/g, "\n\n");

    const lines = prepared
        .split(/\n+/)
        .map((line) => line.trim())
        .filter(Boolean);

    const isSectionStart = (line) => {
        return /^\d+\.\s+/.test(line)
            || /^(Project|Company|Topic|Step|Week|Phase|Action)\s+\d+\s*:/i.test(line)
            || /^\d+\.\s+\*\*[^*]+\*\*:/.test(line);
    };

    const parseSectionTitle = (line, index) => {
        const markdownNumbered = line.match(/^\d+\.\s+\*\*([^*]+)\*\*:\s*(.*)$/);
        if (markdownNumbered) {
            return {
                title: `${sectionPrefix} ${index + 1}: ${markdownNumbered[1].trim()}`,
                remainder: (markdownNumbered[2] || "").trim()
            };
        }

        const named = line.match(/^(Project|Company|Topic|Step|Week|Phase|Action)\s+(\d+)\s*:\s*(.*)$/i);
        if (named) {
            return {
                title: `${named[1]} ${named[2]}${named[3] ? `: ${named[3].trim()}` : ""}`,
                remainder: ""
            };
        }

        const numbered = line.match(/^\d+\.\s+(.*)$/);
        if (numbered) {
            const rawTitle = (numbered[1] || "").trim();
            const split = rawTitle.match(/^([^:]{1,90}):\s*(.*)$/);
            if (split) {
                return {
                    title: `${sectionPrefix} ${index + 1}: ${split[1].trim()}`,
                    remainder: (split[2] || "").trim()
                };
            }
            return {
                title: `${sectionPrefix} ${index + 1}: ${rawTitle}`,
                remainder: ""
            };
        }

        return { title: `${sectionPrefix} ${index + 1}`, remainder: line };
    };

    const introParts = [];
    const sections = [];
    let current = null;

    lines.forEach((line) => {
        if (isSectionStart(line)) {
            if (current) sections.push(current);
            const parsed = parseSectionTitle(line, sections.length);
            current = {
                title: parsed.title,
                paragraphs: parsed.remainder ? [parsed.remainder] : [],
                bullets: []
            };
            return;
        }

        const bullet = line.match(/^[•+\-*]\s+(.*)$/);
        const kv = line.match(/^([A-Za-z][A-Za-z0-9 /&()'\-]{2,40}):\s*(.+)$/);

        if (!current) {
            introParts.push(bullet ? bullet[1].trim() : line);
        } else if (bullet) {
            current.bullets.push(bullet[1].trim());
        } else if (kv) {
            current.bullets.push(`${kv[1].trim()}: ${kv[2].trim()}`);
        } else {
            current.paragraphs.push(line);
        }
    });

    if (current) sections.push(current);

    if (!sections.length) {
        return `
            <div class="resume-section">
                <div class="resume-section-title">${escapeHtml(fallbackHeading)}</div>
                <p class="output-paragraph">${escapeHtml(introParts.join(" ") || raw)}</p>
            </div>
        `;
    }

    return `
        <div style="font-size: 14px; line-height: 1.6;">
            ${introParts.length ? `<div class="resume-section"><div class="resume-section-title">Intro</div><p class="output-paragraph">${escapeHtml(introParts.join(" "))}</p></div>` : ""}
            ${sections.map((section) => `
                <div class="resume-section" style="margin-bottom: 14px;">
                    <div class="resume-section-title">${escapeHtml(section.title)}</div>
                    ${section.paragraphs.length ? section.paragraphs.map((p) => `<p class="output-paragraph">${escapeHtml(p)}</p>`).join("") : ""}
                    ${section.bullets.length ? `<ul class="resume-bullets">${section.bullets.map((b) => `<li>${escapeHtml(b)}</li>`).join("")}</ul>` : ""}
                </div>
            `).join("")}
        </div>
    `;
}

function renderResumeSheet(text) {
    const lines = chunkLines(text);
    const sections = [];
    let current = { title: "Overview", items: [] };

    lines.forEach((line, index) => {
        const isBoldLine = line.startsWith("**") && line.endsWith("**");
        const plain = line.replace(/^\*\*|\*\*$/g, "").trim();
        if (index === 0 && plain && !plain.includes(":") && plain.length < 60) {
            current.title = "Header";
            current.items.push(plain);
            return;
        }
        if (isBoldLine || /^[A-Za-z][A-Za-z\s/&-]{2,}:$/.test(plain)) {
            if (current.items.length) sections.push(current);
            current = { title: plain.replace(/:$/, ""), items: [] };
            return;
        }
        current.items.push(plain);
    });
    if (current.items.length) sections.push(current);

    const headerName = sections[0]?.items?.[0] || "Dronacharya Candidate";
    const contact = sections.find((section) => /contact/i.test(section.title))?.items?.slice(0, 3) || [];
    const summary = sections.find((section) => /summary/i.test(section.title))?.items || [];

    const resumeSections = sections.filter((section) => !/header|contact|summary/i.test(section.title));

    const atsNote = `Your current ATS score is ${lastAtsScore}, below is a pin point resume to get 95+`;

    return `
        <div class="resume-sheet">
            <div class="ats-score-banner" style="background-color: #ffe0e0; border-left: 4px solid #e63946; padding: 12px; margin-bottom: 16px; border-radius: 4px;">
                <p style="color: #e63946; font-weight: 600; margin: 0;">${escapeHtml(atsNote)}</p>
            </div>
            <div class="resume-header">
                <div>
                    <div class="resume-name">${escapeHtml(headerName)}</div>
                    <div class="resume-meta">${escapeHtml(contact.join(" · "))}</div>
                </div>
                <div class="resume-meta">Generated by Dronacharya</div>
            </div>
            ${summary.length ? `
            <div class="resume-section">
                <div class="resume-section-title">Summary</div>
                <p class="output-paragraph">${escapeHtml(summary.join(" "))}</p>
            </div>` : ""}
            ${resumeSections.map((section) => `
                <div class="resume-section">
                    <div class="resume-section-title">${escapeHtml(section.title)}</div>
                    <ul class="resume-bullets">
                        ${section.items.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}
                    </ul>
                </div>
            `).join("")}
        </div>
    `;
}

function splitSentences(text) {
    return String(text || "")
        .replace(/\n+/g, " ")
        .split(/(?<=[.!?])\s+/)
        .map((part) => part.trim())
        .filter(Boolean);
}

function renderBulletTiles(text) {
    const bullets = chunkLines(text)
        .flatMap((line) => line.startsWith("•") ? [line.replace(/^•\s*/, "")] : splitSentences(line))
        .filter(Boolean)
        .slice(0, 8)
        .map((item) => item.replace(/^[-*]\s*/, ""));

    return `<ul class="output-list output-list--bullets">${bullets.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>`;
}

function renderGithubRecommendations(text) {
    const raw = String(text || "")
        .replace(/\r/g, "\n")
        .replace(/\t/g, " ")
        .replace(/\s{2,}/g, " ")
        .trim();

    if (!raw) {
        return '<p class="output-paragraph">No GitHub recommendations available.</p>';
    }

    const actionHeaderRegex = /(Action\s*\d+\s*:|\d+\.\s+\*\*[^*]+\*\*:)/gi;
    const matches = Array.from(raw.matchAll(actionHeaderRegex));

    if (!matches.length) {
        return `<div class="output-fallback">${escapeHtml(raw)}</div>`;
    }

    const firstHeaderIndex = matches[0].index || 0;
    const intro = raw.slice(0, firstHeaderIndex).trim();

    const actions = matches.map((m, idx) => {
        const start = m.index || 0;
        const end = idx + 1 < matches.length ? (matches[idx + 1].index || raw.length) : raw.length;
        const block = raw.slice(start, end).trim();

        let title = `Action ${idx + 1}`;
        let content = block;

        const numberedMatch = block.match(/^\d+\.\s+\*\*([^*]+)\*\*:\s*([\s\S]*)$/i);
        if (numberedMatch) {
            title = `Action ${idx + 1}: ${numberedMatch[1].trim()}`;
            content = (numberedMatch[2] || "").trim();
        } else {
            const actionMatch = block.match(/^Action\s*(\d+)\s*:\s*([\s\S]*)$/i);
            if (actionMatch) {
                const rest = (actionMatch[2] || "").trim();
                const splitAt = rest.search(/\s[•+\-*]\s/);
                if (splitAt > 0) {
                    title = `Action ${actionMatch[1]}: ${rest.slice(0, splitAt).trim()}`;
                    content = rest.slice(splitAt).trim();
                } else {
                    title = `Action ${actionMatch[1]}`;
                    content = rest;
                }
            }
        }

        const bulletish = content
            .replace(/\s([•+\-*])\s/g, "\n$1 ")
            .split(/\n+/)
            .map((line) => line.trim())
            .filter(Boolean);

        const bullets = bulletish
            .filter((line) => /^[•+\-*]\s+/.test(line))
            .map((line) => line.replace(/^[•+\-*]\s+/, "").trim());

        const paragraph = bulletish
            .filter((line) => !/^[•+\-*]\s+/.test(line))
            .join(" ")
            .trim();

        return { title, bullets, paragraph };
    });

    return `
        <div style="font-size: 14px; line-height: 1.6;">
            ${intro ? `<p style="color: #666; margin-bottom: 16px;">${escapeHtml(intro)}</p>` : ""}
            <div class="tile-grid" style="grid-template-columns: 1fr; gap: 12px;">
                ${actions.map((action) => `
                    <div class="mini-tile" style="padding: 14px; border-left: 3px solid #0366d6;">
                        <div class="mini-tile-title" style="font-size: 14px; font-weight: 700; margin-bottom: 10px; color: #0366d6;">${escapeHtml(action.title)}</div>
                        ${action.paragraph ? `<p class="output-paragraph" style="margin: 0 0 8px 0;">${escapeHtml(action.paragraph)}</p>` : ""}
                        ${action.bullets.length ? `<ul class="resume-bullets" style="margin: 0;">${action.bullets.map((b) => `<li>${escapeHtml(b)}</li>`).join("")}</ul>` : ""}
                    </div>
                `).join("")}
            </div>
        </div>
    `;
}

function renderMiniTiles(text) {
    const chunks = splitChunks(text)
        .flatMap((chunk) => splitSentences(chunk))
        .filter(Boolean)
        .slice(0, 4)
        .map((item) => item.replace(/^[-*]\s*/, ""));

    return `<div class="tile-grid" style="grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 16px;">${chunks.map((item, index) => `<div class="mini-tile"><div class="mini-tile-title">Project ${index + 1}</div><div class="mini-tile-body" style="min-height: 100px; display: flex; align-items: center;">${escapeHtml(item)}</div></div>`).join("")}</div>`;
}

function renderCompanyTiles(text) {
    const lines = chunkLines(text);
    const companies = [];
    let current = { name: "", reqs: [] };
    
    lines.forEach((line) => {
        if (/^(MNC|Company|\d+\.|[A-Z][a-z]+)\s*[:]*\s+/.test(line) && current.name) {
            if (current.reqs.length > 0) companies.push({...current});
            current = { name: line.replace(/^(MNC|Company|\d+\.|)\s*[:]*\s*/, "").substring(0, 30), reqs: [] };
        } else if (line && current.name === "") {
            current.name = line.substring(0, 30);
        } else if (line && current.name) {
            current.reqs.push(line);
        }
    });
    if (current.name && current.reqs.length > 0) companies.push(current);
    
    const validCompanies = companies.slice(0, 12);
    if (validCompanies.length === 0) {
        const chunks = splitChunks(text).slice(0, 12);
        return `<div class="tile-grid">${chunks.map((item, index) => `<div class="mini-tile"><div class="mini-tile-title">MNC ${index + 1}</div><div class="mini-tile-body">${escapeHtml(item)}</div></div>`).join("")}</div>`;
    }
    
    return `<div class="tile-grid">${validCompanies.map((comp, index) => `<div class="mini-tile"><div class="mini-tile-title">${escapeHtml(comp.name)}</div><div class="mini-tile-body"><ul style="padding-left: 16px; margin: 0;">${comp.reqs.slice(0, 3).map(r => `<li style="font-size: 13px; margin: 4px 0;">${escapeHtml(r)}</li>`).join("")}</ul></div></div>`).join("")}</div>`;
}

function renderChecklist(text) {
    const items = splitChunks(text)
        .flatMap((chunk) => splitSentences(chunk))
        .filter(Boolean)
        .slice(0, 12)
        .map((item) => item.replace(/^[-*]\s*/, ""));

    return `<ul class="checklist">${items.map((item) => `<li>${escapeHtml(item)}</li>`).join("")}</ul>`;
}

function renderDeadlinesContent(text) {
    const parts = splitChunks(text).flatMap((chunk) => splitSentences(chunk)).filter(Boolean);
    if (!parts.length) {
        return '<p class="output-paragraph">No deadline plan available.</p>';
    }

    const intro = parts[0];
    const steps = parts.slice(1, 10);

    return `
        <div class="deadline-intro">${escapeHtml(intro)}</div>
        <div class="tile-grid">
            ${steps.map((item, index) => `
                <div class="mini-tile">
                    <div class="mini-tile-title">Step ${index + 1}</div>
                    <div class="mini-tile-body">${escapeHtml(item)}</div>
                </div>
            `).join("")}
        </div>
    `;
}

function downloadPdf(content, fileName = "dream-resume.pdf") {
    const element = document.createElement("a");
    const file = new Blob([content], {type: "text/plain"});
    element.href = URL.createObjectURL(file);
    element.download = fileName;
    document.body.appendChild(element);
    element.click();
    document.body.removeChild(element);
}

function getActionSpecificButtons(action) {
    const buttonMap = {
        "dream-cv": `
            <div style="display: flex; gap: 8px; margin-top: 12px;">
                <button type="button" class="btn btn-secondary" onclick="confirmDownloadPdf()">📥 Download PDF</button>
            </div>
        `,
        "github": `
            <div style="display: flex; gap: 8px; margin-top: 12px;">
                <button type="button" class="btn btn-secondary" onclick="window.open('https://github.com', '_blank')">🐙 Go to GitHub</button>
            </div>
        `,
        "projects": "",
        "deadlines": `
            <div style="display: flex; gap: 8px; margin-top: 12px;">
                <button type="button" class="btn btn-secondary" onclick="window.open('https://calendar.google.com', '_blank')">📅 Add to Calendar</button>
            </div>
        `,
        "mnc-openings": "",
        "topics": `
            <div style="display: flex; gap: 8px; margin-top: 12px;">
                <button type="button" class="btn btn-secondary" onclick="window.open('https://notes.google.com', '_blank')">📝 Save to Google Notes</button>
            </div>
        `,
    };
    return buttonMap[action] || "";
}

function confirmDownloadPdf() {
    const content = document.querySelector(".output-content").innerText;
    if (content) {
        downloadPdf(content, "Dream-Resume.txt");
        showNotification("Resume downloaded!", "success");
    } else {
        showNotification("No content to download", "error");
    }
}
