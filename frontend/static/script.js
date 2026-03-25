let DEFAULT_CONFIG= {};

fetch("/config")
  .then(r => r.json())
  .then(data => {
      DEFAULT_CONFIG = data;
      console.log(DEFAULT_CONFIG.models.llm_model);
  });

let ws;
let sessionId = null;
let topicChart = null;
let currentEvaluationSession = null;

window.addEventListener("DOMContentLoaded", () => {
    document.getElementById("evaluation-screen").style.display = "none";

    const toggleBtn = document.getElementById("toggleConfig");
    if(toggleBtn){
        toggleBtn.onclick = () => {
            document.getElementById("setup-screen").style.display = "none";
            const panel = document.getElementById("config-panel");
            panel.style.display =
                panel.style.display === "none" ? "block" : "none";
        };
    }
        /* SLIDER VALUE DISPLAY */
    document.querySelectorAll(".policy-block input[type='range']").forEach(slider => {

        const label = slider.parentElement.querySelector(".slider-value");

        if(label){
            label.textContent = slider.value;
        }

        slider.addEventListener("input", () => {

            const block = slider.closest(".policy-block");

            normalizeGroup(block);   // normalize probabilities

            // update labels after normalization
            block.querySelectorAll("input[type='range']").forEach(s => {

                const l = s.parentElement.querySelector(".slider-value");

                if(l){
                    l.textContent = s.value;
                }

            });

        });

    });

    const resetBtn = document.getElementById("resetConfig");

    if(resetBtn){

        resetBtn.onclick = () => {

            applyConfig(DEFAULT_CONFIG);

        };

    }  
    document.getElementById("viewTranscriptBtn").onclick = viewTranscript;

    document.getElementById("closeTranscriptModal").onclick = () => {

        document.getElementById("transcript-modal").style.display = "none";

    };
    window.onclick = function(event){

        const modal = document.getElementById("transcript-modal");

        if(event.target === modal){
            modal.style.display = "none";
        }

    };


});


function saveApiKey() {

    const key = document.getElementById("apiKey").value.trim();

    fetch("/api_key", {
        method: "POST",
        headers: {
            "Content-Type": "application/x-www-form-urlencoded"
        },
        body: new URLSearchParams({
            api_key: key
        })
    })
    .then(() => alert("API Key saved"));
}

function toggleInputMethod() {
    const method = document.querySelector('input[name="inputMethod"]:checked').value;

    document.getElementById("resume-section").style.display =
        method === "resume" ? "block" : "none";

    // document.getElementById("profile-section").style.display =
    //     method === "profile" ? "block" : "none";
}

function openProfile() {
    document.getElementById("setup-screen").style.display = "none";
    document.getElementById("profile-screen").style.display = "block";
    loadProfile();
}


function addExperience() {
    const container = document.getElementById("experience-container");
    const div = document.createElement("div");
    div.classList.add("exp-block");
    const idx = container.children.length + 1;
    div.innerHTML = `
        <div class="block-header">
            <span class="block-index">EXP · ${String(idx).padStart(2, '0')}</span>
            <button class="remove-btn"
                onclick="this.closest('.exp-block').remove(); updateCounts();">✕</button>
        </div>
        <div class="input-grid">
            <div class="input-group">
                <label>Company</label>
                <input type="text" placeholder="Google, Meta..." class="exp-company">
            </div>
            <div class="input-group">
                <label>Role</label>
                <input type="text" placeholder="Software Engineer" class="exp-role">
            </div>
            <div class="input-group">
                <label>From</label>
                <input type="date" class="exp-from">
            </div>
            <div class="input-group">
                <label>To</label>
                <input type="date" class="exp-to">
            </div>
            <div class="input-group full-width">
                <label>Points</label>
                <textarea placeholder="One point per line" class="exp-points"></textarea>
            </div>
        </div>`;
    container.appendChild(div);
    updateCounts();
    div.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

function addProject() {
    const container = document.getElementById("project-container");
    const div = document.createElement("div");
    div.classList.add("proj-block");
    const idx = container.children.length + 1;
    div.innerHTML = `
        <div class="block-header">
            <span class="block-index">PROJ · ${String(idx).padStart(2, '0')}</span>
            <button class="remove-btn"
                onclick="this.closest('.proj-block').remove(); updateCounts();">✕</button>
        </div>
        <div class="input-grid">
            <div class="input-group">
                <label>Project Name</label>
                <input type="text" placeholder="My Awesome Project" class="proj-name">
            </div>
            <div class="input-group">
                <label>Tech Stack</label>
                <input type="text" placeholder="React, Node, Postgres" class="proj-tech">
            </div>
            <div class="input-group full-width">
                <label>Link (optional)</label>
                <input type="text" placeholder="https://github.com/..." class="proj-link">
            </div>
            <div class="input-group full-width">
                <label>Points</label>
                <textarea placeholder="One point per line" class="proj-points"></textarea>
            </div>
        </div>`;
    container.appendChild(div);
    updateCounts();
    div.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

function updateCounts() {
    const exp = document.querySelectorAll(".exp-block").length;
    const proj = document.querySelectorAll(".proj-block").length;
    document.getElementById("exp-count").textContent =
        exp + (exp === 1 ? " entry" : " entries");
    document.getElementById("proj-count").textContent =
        proj + (proj === 1 ? " entry" : " entries");
}

function buildProfileJSON() {
    const experiences = [];
    document.querySelectorAll(".exp-block").forEach(block => {
        const company = block.querySelector(".exp-company").value;
        const role = block.querySelector(".exp-role").value;
        const from = block.querySelector(".exp-from").value;
        const to = block.querySelector(".exp-to").value;
        const points = block.querySelector(".exp-points").value
            .split("\n").map(p => p.trim()).filter(p => p);
        if (company || role || points.length) {
            experiences.push({ company, role, from, to, points });
        }
    });

    const projects = [];
    document.querySelectorAll(".proj-block").forEach(block => {
        const name = block.querySelector(".proj-name").value;
        const tech = block.querySelector(".proj-tech").value;
        const link = block.querySelector(".proj-link").value;
        const points = block.querySelector(".proj-points").value
            .split("\n").map(p => p.trim()).filter(p => p);
        if (name || points.length) {
            projects.push({ name, tech, link, points });
        }
    });

    const skills = document.getElementById("skillsInput").value
        .split(",").map(s => s.trim()).filter(s => s);
    const achievements = document.getElementById("achievementsInput").value
        .split("\n").map(a => a.trim()).filter(a => a);

    return {
        experience: experiences,
        projects: projects,
        skills: skills,
        achievements: achievements,
        research: []
    };
}

function saveProfile() {
    const profile = buildProfileJSON();
    fetch("/profile", {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body: new URLSearchParams({ profile: JSON.stringify(profile) })
    })
    .then(() => {
        const btn = document.querySelector(".save-btn");
        btn.textContent = "✓ Saved!";
        btn.style.background = "linear-gradient(135deg, #059669, #10b981)";
        setTimeout(() => {
            btn.textContent = "Save Profile";
            btn.style.background = "";
        }, 1800);
    });
}

function loadProfile() {
    fetch("/profile")
        .then(res => res.json())
        .then(data => {
            const profile = data.profile;
            document.getElementById("experience-container").innerHTML = "";
            document.getElementById("project-container").innerHTML = "";
            if (!profile) return;

            // Experience
            profile.experience.forEach(exp => {
                addExperience();
                const blocks = document.querySelectorAll(".exp-block");
                const last = blocks[blocks.length - 1];
                last.querySelector(".exp-company").value = exp.company || "";
                last.querySelector(".exp-role").value = exp.role || "";
                last.querySelector(".exp-points").value = (exp.points || []).join("\n");
                // new optional fields — only fill if data exists
                if (exp.from) last.querySelector(".exp-from").value = exp.from;
                if (exp.to)   last.querySelector(".exp-to").value   = exp.to;
            });

            // Projects
            profile.projects.forEach(proj => {
                addProject();
                const blocks = document.querySelectorAll(".proj-block");
                const last = blocks[blocks.length - 1];
                last.querySelector(".proj-name").value = proj.name || "";
                last.querySelector(".proj-points").value = (proj.points || []).join("\n");
                // new optional fields — only fill if data exists
                if (proj.tech) last.querySelector(".proj-tech").value = proj.tech;
                if (proj.link) last.querySelector(".proj-link").value = proj.link;
            });

            // Skills
            document.getElementById("skillsInput").value =
                (profile.skills || []).join(", ");

            // Achievements
            document.getElementById("achievementsInput").value =
                (profile.achievements || []).join("\n");

            updateCounts();
        });
}


// --- Setup Function ---
async function startInterview() {

    const preparingMsg = addSystemMessage("Preparing your interview... This may take a few seconds.");
    enableInput(false);

    const config = {
        api: {
            groq_api_key:
                document.getElementById("apiKey")?.value ||
                DEFAULT_CONFIG.api.groq_api_key
        },
        models: {
            llm_model: DEFAULT_CONFIG.models.llm_model,
            embedding_model: DEFAULT_CONFIG.models.embedding_model
        },
        interview: {
            questions_per_topic:
                parseInt(document.getElementById("questionsPerTopic")?.value) ||
                DEFAULT_CONFIG.interview.questions_per_topic,
            max_topics:
                parseInt(document.getElementById("maxTopics")?.value) ||
                DEFAULT_CONFIG.interview.max_topics,
            difficulty:
                document.getElementById("difficulty")?.value ||
                DEFAULT_CONFIG.interview.difficulty,        // ← was DEFAULT_CONFIG.difficulty (wrong path)
            thresholds: {
                weak:
                    parseFloat(document.getElementById("weakThreshold")?.value) ||
                    DEFAULT_CONFIG.interview.thresholds.weak,
                medium:
                    parseFloat(document.getElementById("mediumThreshold")?.value) ||
                    DEFAULT_CONFIG.interview.thresholds.medium  // ← was DEFAULT_CONFIG.intervie (typo)
                },
            policy: {
                start: {
                    theory:
                        parseFloat(document.getElementById("startTheory")?.value) ||
                        DEFAULT_CONFIG.interview.policy.start.theory,
                    applied:
                        parseFloat(document.getElementById("startApplied")?.value) ||
                        DEFAULT_CONFIG.interview.policy.start.applied
                },
                weak: {
                    clarification:
                        parseFloat(document.getElementById("weakClarification")?.value) ||
                        DEFAULT_CONFIG.interview.policy.weak.clarification,
                    theory:
                        parseFloat(document.getElementById("weakTheory")?.value) ||
                        DEFAULT_CONFIG.interview.policy.weak.theory
                },
                medium: {
                    depth:
                        parseFloat(document.getElementById("mediumDepth")?.value) ||
                        DEFAULT_CONFIG.interview.policy.medium.depth,
                        theory:
                        parseFloat(document.getElementById("mediumTheory")?.value) ||
                        DEFAULT_CONFIG.interview.policy.medium.theory,
                    applied:
                        parseFloat(document.getElementById("mediumApplied")?.value) ||
                        DEFAULT_CONFIG.interview.policy.medium.applied
                },
                strong: {
                    applied:
                        parseFloat(document.getElementById("strongApplied")?.value) ||
                        DEFAULT_CONFIG.interview.policy.strong.applied,
                    depth:
                        parseFloat(document.getElementById("strongDepth")?.value) ||
                        DEFAULT_CONFIG.interview.policy.strong.depth,
                    theory:
                        parseFloat(document.getElementById("strongTheory")?.value) ||
                        DEFAULT_CONFIG.interview.policy.strong.theory
                }
            }
        },
        logging: {
            on: DEFAULT_CONFIG.logging.on,
            level: DEFAULT_CONFIG.logging.level
        }
    };

    const role = document.getElementById('jobRole').value;
    const jd = document.getElementById('jobDescription').value;
    const method = document.querySelector('input[name="inputMethod"]:checked').value;

    if (!role) return alert("Please enter a job role");
    if (!jd) return alert("Please paste the job description");
    
    // --- UI Transition ---
    document.getElementById('setup-screen').style.display = 'none';
    document.getElementById('afterInterview').style.display = 'none';
    document.getElementById('chat-screen').style.display = 'flex';
    document.getElementById('status').style.color = 'orange';
    document.getElementById('status').innerText = '● Preparing';
    document.getElementById('role-display').innerText = role + " Interview";

    // --- Send data to backend ---
    const formData = new FormData();
    formData.append("role", role);
    formData.append("jd", jd);
    formData.append("config", JSON.stringify(config));

    if (method === "profile") {

    } else {
        const fileInput = document.getElementById("resumeFile");
        const resumeFile = fileInput.files[0];

        if (!resumeFile) {
            return alert("Please upload your resume");
        }

        formData.append("resume", resumeFile);
    }

    const response = await fetch("/setup", {
        method: "POST",
        body: formData
    });
    const data = await response.json();
    sessionId = data.session_id;
    console.log("SESSION ID:", sessionId);

    // --- WebSocket connection ---
    const protocol = window.location.protocol === "https:" ? "wss" : "ws";
    
    ws = new WebSocket(
        `${protocol}://${window.location.host}/ws/interview/${sessionId}`
    );
    
    ws.onopen = function () {
        console.log("Connected to Interview Server");
        document.getElementById('status').style.color = 'green';
        document.getElementById('status').innerText = '● Live';
    };
    
    
    ws.onmessage = function (event) {

        const data = event.data;

        if (preparingMsg && preparingMsg.parentNode) {  
            preparingMsg.remove();
        }

        if (data.startsWith("SYSTEM_TURN:USER")) {
            enableInput(true);
            return;
        }

        if (data.startsWith("SYSTEM_INFO:")) {
            addSystemMessage(data.split(":")[1]);
            return;
        }

        if (data.startsWith("SYSTEM_END:")) {
            addSystemMessage("Interview Finished.");
            enableInput(false);
            document.getElementById('status').style.color = 'red';
            document.getElementById('status').innerText = '● Finished';
            document.getElementById('afterInterview').style.display = 'flex';
            ws.close();
            return;
        }

        const firstColon = data.indexOf(':');

        if (firstColon > -1) {
            const source = data.substring(0, firstColon);
            const content = data.substring(firstColon + 1);
            addMessage(source, content);
        }
    };

    ws.onclose = function () {
        document.getElementById('status').style.color = 'gray';
        document.getElementById('status').innerText = '● Disconnected';
    };
}

// --- Chat Functions ---

function addMessage(source, content) {
    if(source === 'Candidate') return;

    const messagesDiv = document.getElementById('messages');
    const bubble = document.createElement('div');
    
    let type = 'interviewer';
    if(source === 'Evaluator') type = 'evaluator';

    bubble.className = `message ${type}`;
    
    const nameSpan = document.createElement('div');
    nameSpan.className = 'sender-name';
    nameSpan.innerText = source;

    const textSpan = document.createElement('div');
    textSpan.innerText = content;

    bubble.appendChild(nameSpan);
    bubble.appendChild(textSpan);
    messagesDiv.appendChild(bubble);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
}

function addSystemMessage(text) {
    const messagesDiv = document.getElementById('messages');
    const div = document.createElement('div');
    div.className = 'system-message';
    div.innerText = text;
    messagesDiv.appendChild(div);
    return div;

}

function sendMsg() {

    const input = document.getElementById('msgInput');
    const text = input.value.trim();
    if(!text) return;

    const messagesDiv = document.getElementById('messages');
    const bubble = document.createElement('div');
    bubble.className = 'message user';
    bubble.innerText = text;

    messagesDiv.appendChild(bubble);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;

    ws.send(text);

    input.value = '';
    input.style.height = "auto";   // reset textarea
    enableInput(false);
}

function enableInput(enabled) {
    const input = document.getElementById('msgInput');
    input.disabled = !enabled;
    if(enabled) input.focus();
}


async function getEvaluation() {
    if (!sessionId) return;

    // Immediately swap screens
    document.getElementById("chat-screen").style.display = "none";
    document.getElementById("messages").innerHTML = ""; // clear chat from chat-screen

    document.getElementById("evaluation-loading-screen").style.display = "flex";

    // Animate steps + progress bar while waiting
    const steps = ["step-1", "step-2", "step-3"];
    const progressFill = document.getElementById("evalProgressFill");
    const progressTargets = [25, 55, 80];
    let stepIndex = 0;

    function activateNextStep() {
        if (stepIndex > 0) {
            document.getElementById(steps[stepIndex - 1]).classList.remove("active");
            document.getElementById(steps[stepIndex - 1]).classList.add("done");
        }
        if (stepIndex < steps.length) {
            document.getElementById(steps[stepIndex]).classList.add("active");
            progressFill.style.width = progressTargets[stepIndex] + "%";
            stepIndex++;
        }
    }

    activateNextStep(); // step 1 immediately
    const t1 = setTimeout(() => activateNextStep(), 1800);  // step 2
    const t2 = setTimeout(() => activateNextStep(), 3800);  // step 3

    try {
        const response = await fetch(`/evaluation/${sessionId}`);
        currentEvaluationSession = sessionId;
        const data = await response.json();

        // Complete progress before transition
        clearTimeout(t1); clearTimeout(t2);
        steps.forEach(id => {
            const el = document.getElementById(id);
            el.classList.remove("active");
            el.classList.add("done");
        });
        progressFill.style.width = "100%";

        await new Promise(r => setTimeout(r, 500)); // brief pause at 100%

        document.getElementById("evaluation-loading-screen").style.display = "none";
        document.getElementById("evaluation-screen").style.display = "block";
        renderEvaluation(data.report, data.report_data);

    } catch (err) {
        clearTimeout(t1); clearTimeout(t2);
        document.getElementById("evaluation-loading-screen").style.display = "none";
        document.getElementById("chat-screen").style.display = "flex"; // or however you show it
        console.error("Evaluation failed:", err);
    }
}

function formatReport(text) {
    // Remove * and # characters
    text = text.replace(/[*#]/g, '');

    const headings = [
        "Interview Summary",
        "Key Strengths",
        "Areas for Improvement",
        "Final Evaluation",
        "Recommendations",
        "Interview Evaluation Report"
    ];

    // Replace headings with styled section headers
    headings.forEach(heading => {
        text = text.replace(
            new RegExp(heading, 'g'),
            `</div><div class="report-section">
                <div class="report-heading">${heading}</div>`
        );
    });

    // Preserve line breaks
    text = text.replace(/\n/g, '<br>');

    // Wrap everything and close the last open div
    text = `${text}</div>`;

    return text;
}

function renderEvaluation(report, reportData){


    document.getElementById("setup-screen").style.display = "none";
    document.getElementById("evaluation-screen").style.display = "block";

    /* SCORE */
    document.getElementById("score-value").innerText = (reportData.overall_score * 100).toFixed(2) + "%";
    console.log(reportData.overall_score);
    console.log(typeof reportData.overall_score);

    /* STRENGTHS */
    const strengthList = document.getElementById("strength-list");
    strengthList.innerHTML = "";

    reportData.strengths.forEach(s => {
        const li = document.createElement("li");
        li.innerText = s;
        strengthList.appendChild(li);
    });

    /* WEAKNESSES */
    const weaknessList = document.getElementById("weakness-list");
    weaknessList.innerHTML = "";

    reportData.weaknesses.forEach(w => {
        const li = document.createElement("li");
        li.innerText = w;
        weaknessList.appendChild(li);
    });
    
    /* TOPIC CHART */
    const labels = Object.keys(reportData.topic_scores).map(label =>
        label.split(" ")
    );

    const values = Object.values(reportData.topic_scores).map(v => Math.round(v * 100));

    const ctx = document.getElementById("topicChart").getContext("2d");

    const gradient = ctx.createLinearGradient(0, 0, 0, 400);
    gradient.addColorStop(0, 'rgba(241, 168, 99, 0.9)');    // orange top
    gradient.addColorStop(1, 'rgba(229, 70, 208, 0.7)'); 

    if (topicChart) {
        topicChart.destroy();
    }

    topicChart = new Chart(ctx, {
        type: "bar",
        data: {
            labels: labels,
            datasets: [{
                label: "Score %",
                data: values,
                backgroundColor: gradient,
                borderColor: 'rgba(229, 70, 208, 0.9)',
                borderWidth: 1,
                borderRadius: 6,
                hoverBackgroundColor: 'rgba(241, 100, 220, 0.75)',
            }]
        },
        options: {
            plugins: {
                legend: {
                    labels: {
                        color: '#4a6fa5',
                        font: { family: 'DM Mono', size: 11 }
                    }
                },
                tooltip: {
                    backgroundColor: 'rgba(10, 22, 40, 0.95)',
                    borderColor: 'rgba(229, 70, 208, 0.4)',
                    borderWidth: 1,
                    titleColor: '#e8f0fe',
                    bodyColor: '#93b4dc',
                    titleFont: { family: 'DM Mono', size: 11 },
                    bodyFont: { family: 'DM Mono', size: 11 },
                    callbacks: {
                        label: ctx => ` ${ctx.parsed.y}%`
                    }
                }
            },
            scales: {
                x: {
                    ticks: {
                        color: '#4a6fa5',
                        font: { family: 'DM Mono', size: 11 }
                    },
                    grid: {
                        color: 'rgba(77, 139, 255, 0.06)'
                    },
                    border: {
                        color: 'rgba(77, 139, 255, 0.15)'
                    }
                },
                y: {
                    beginAtZero: true,
                    max: 100,
                    ticks: {
                        color: '#4a6fa5',
                        font: { family: 'DM Mono', size: 11 },
                        callback: value => value + "%"
                    },
                    grid: {
                        color: 'rgba(77, 139, 255, 0.06)'
                    },
                    border: {
                        color: 'rgba(77, 139, 255, 0.15)'
                    }
                }
            }
        }
    });

    /* SUMMARY */

    if (report) {
        document.getElementById("evaluation-text").innerHTML = formatReport(report);
    }
    else {
        document.getElementsByClassName("summary-section")[0].style.display = "none";
    }


}

function debugEvaluation(){

    const testSessionId = prompt("Enter session ID to load evaluation:");

    if(!testSessionId) return;

    sessionId = testSessionId;

    getEvaluation();
}

function openHistory(){

    document.getElementById("setup-screen").style.display = "none";
    document.getElementById("history-screen").style.display = "block";

    loadHistory();

}

function goBack(screen){

    document.getElementById("config-panel").style.display = "none";
    document.getElementById("profile-screen").style.display = "none";
    document.getElementById("evaluation-screen").style.display = "none";
    document.getElementById("history-screen").style.display = "none";
    document.getElementById("setup-screen").style.display = "block";
}   

async function loadHistory(){

    const response = await fetch("/interviews");
    const data = await response.json();

    const table = document.querySelector("#history-table tbody");
    table.innerHTML = "";

    data.forEach(interview => {

        const row = document.createElement("tr");

        let scoreClass = "score-bad";

        if(interview.overall_score > 0.75)
            scoreClass = "score-good";
        else if(interview.overall_score > 0.5)
            scoreClass = "score-medium";

        const { dateStr, timeStr } = formatDateTime(interview.date);

        row.innerHTML = `
            <td>${dateStr}</td>
            <td>${timeStr}</td> 
            <td>${interview.job_role}</td>
            <td class="${scoreClass}">
                ${(interview.overall_score * 100).toFixed(1)}%
            </td>
            <td>${interview.session_id.slice(0, 8)}...</td>
        `;

        row.onclick = async () => {

            // hide history
            document.getElementById("loading-overlay").style.display = "flex";
            const response = await fetch(`/evaluation-nollm/${interview.session_id}`);
            currentEvaluationSession = interview.session_id;
            const data = await response.json();
            
            const report = data.report;
            const report_data = data.report_data;
            document.getElementById("history-screen").style.display = "none";
            document.getElementById("loading-overlay").style.display = "none";
            
            renderEvaluation(report, report_data);

        };

        table.appendChild(row);

    });

}

function formatDateTime(isoString) {
    const date = new Date(isoString + "Z"); // Ensure it's treated as UTC
    const dateStr = date.toLocaleDateString('en-IN', {
        day: '2-digit',
        month: 'short',
        year: 'numeric'
    });
    const timeStr = date.toLocaleTimeString('en-IN', {
        hour: '2-digit',
        minute: '2-digit',
        hour12: true
    });
    return { dateStr, timeStr };
}

const textarea = document.getElementById("msgInput");

textarea.addEventListener("keydown", function(event){

    // ENTER without Shift → send
    if(event.key === "Enter" && !event.shiftKey){

        event.preventDefault();
        sendMsg();

    }

});

textarea.addEventListener("input", () => {

    textarea.style.height = "auto";
    textarea.style.height = textarea.scrollHeight + "px";

});



function normalizeGroup(block){

    const sliders = block.querySelectorAll("input[type='range']");

    let total = 0;

    sliders.forEach(slider => {
        total += parseFloat(slider.value);
    });

    if(total === 0) return;

    sliders.forEach(slider => {

        const normalized = slider.value / total;

        slider.value = normalized.toFixed(2);

        const label = slider.parentElement.querySelector(".slider-value");
        label.textContent = slider.value;

    });

}

function applyConfig(config){

    document.getElementById("apiKey").value = config.api_key;

    document.getElementById("questionsPerTopic").value =
        config.interview.questions_per_topic;

    document.getElementById("difficulty").value =
        config.interview.difficulty;

    document.getElementById("weakThreshold").value =
        config.interview.thresholds.weak;

    document.getElementById("mediumThreshold").value =
        config.interview.thresholds.medium;

    /* POLICY */

    document.getElementById("startTheory").value =
        config.interview.policy.start.theory;

    document.getElementById("startApplied").value =
        config.interview.policy.start.applied;

    document.getElementById("weakClarification").value =
        config.interview.policy.weak.clarification;

    document.getElementById("weakTheory").value =
        config.interview.policy.weak.theory;

    document.getElementById("mediumDepth").value =
        config.interview.policy.medium.depth;

    document.getElementById("mediumTheory").value =
        config.interview.policy.medium.theory;

    document.getElementById("mediumApplied").value =
        config.interview.policy.medium.applied;

    document.getElementById("strongApplied").value =
        config.interview.policy.strong.applied;

    document.getElementById("strongDepth").value =
        config.interview.policy.strong.depth;

    document.getElementById("strongTheory").value =
        config.interview.policy.strong.theory;

    document.querySelectorAll(".slider-row").forEach(row => {

        const slider = row.querySelector("input[type='range']");
        const label = row.querySelector(".slider-value");

        if(slider && label){
            label.textContent = slider.value;
        }

    });

}

// transcript

async function viewTranscript(){

    console.log("Viewing transcript for session:", currentEvaluationSession);

    const response = await fetch(`/transcript/${currentEvaluationSession}`);

    const data = await response.json();

    const container = document.getElementById("transcript-messages");

    container.innerHTML = "";

    data.transcript.forEach(msg => {

        const bubble = document.createElement("div");

        bubble.className =
            msg.role === "interviewer"
            ? "message interviewer"
            : "message user";

        bubble.innerText = msg.content;

        container.appendChild(bubble);

    });

    document.getElementById("transcript-modal").style.display = "flex";

}   