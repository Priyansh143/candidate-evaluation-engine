let ws;
let sessionId = null;
let topicChart = null;
let currentEvaluationSession = null;
const DEFAULT_CONFIG = {

    api_key: "",

    interview: {
        questions_per_topic: 3,

        difficulty: "medium",   

        thresholds: {
            weak: 0.5,
            medium: 0.75
        },

        policy: {
            start: { theory: 0.6, applied: 0.4 },
            weak: { clarification: 0.8, theory: 0.2 },
            medium: { depth: 0.5, theory: 0.3, applied: 0.2 },
            strong: { applied: 0.5, depth: 0.3, theory: 0.2 }
        }
    }

};



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

// --- Setup Function ---
async function startInterview() {

    const config = {

        api_key:
            document.getElementById("apiKey")?.value || DEFAULT_CONFIG.api_key,

        interview: {

            questions_per_topic:
                parseInt(document.getElementById("questionsPerTopic")?.value) ||
                DEFAULT_CONFIG.interview.questions_per_topic,

            difficulty:
                document.getElementById("difficulty")?.value ||
                DEFAULT_CONFIG.difficulty,

            thresholds: {

                weak:
                    parseFloat(document.getElementById("weakThreshold")?.value) ||
                    DEFAULT_CONFIG.interview.thresholds.weak,

                medium:
                    parseFloat(document.getElementById("mediumThreshold")?.value) ||
                    DEFAULT_CONFIG.intervie.thresholds.medium

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
        }
    };

    document.getElementById("evaluation-screen").style.display = "none";

    const role = document.getElementById('jobRole').value;
    const jd = document.getElementById('jobDescription').value;
    const resumeFile = document.getElementById('resumeFile').files[0];

    if (!role) return alert("Please enter a job role");
    if (!jd) return alert("Please paste the job description");
    if (!resumeFile) return alert("Please upload your resume");

    // --- Send data to backend ---
    const formData = new FormData();
    formData.append("role", role);
    formData.append("jd", jd);
    formData.append("resume", resumeFile);
    formData.append("config", JSON.stringify(config));

    const response = await fetch("/setup", {
        method: "POST",
        body: formData
    });
    const data = await response.json();
    sessionId = data.session_id;
    console.log("SESSION ID:", sessionId);

    // --- UI Transition ---
    document.getElementById('setup-screen').style.display = 'none';
    document.getElementById('chat-screen').style.display = 'flex';
    document.getElementById('role-display').innerText = role + " Interview";

    // --- WebSocket connection ---
    const protocol = window.location.protocol === "https:" ? "wss" : "ws";

    ws = new WebSocket(
        `${protocol}://${window.location.host}/ws/interview/${sessionId}`
    );

    ws.onopen = function () {
        console.log("Connected to Interview Server");
    };

    ws.onmessage = function (event) {

        const data = event.data;

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
            document.getElementById('evaluationBtn').style.display = 'block';
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
    // If source is 'Candidate', ignore it because we already rendered the user's message manually
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
    div.style.textAlign = 'center';
    div.style.color = '#9ca3af';
    div.style.fontSize = '0.8rem';
    div.style.margin = '10px 0';
    div.innerText = text;
    messagesDiv.appendChild(div);
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

async function getEvaluation(){

    if (!sessionId) return;

    const response = await fetch(`/evaluation/${sessionId}`);
    currentEvaluationSession = sessionId;
    const data = await response.json();

    document.getElementById("chat-screen").style.display = "none";
    document.getElementById("evaluation-screen").style.display = "block";

    renderEvaluation(data.report, data.report_data);

}

function renderEvaluation(report, reportData){


    document.getElementById("setup-screen").style.display = "none";
    document.getElementById("evaluation-screen").style.display = "block";

    /* SCORE */
    document.getElementById("score-value").innerText = reportData.overall_score;

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
    gradient.addColorStop(0, "#f1a863");
    gradient.addColorStop(1, "#e546d0");

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
                backgroundColor: gradient
            }]
        },

        options: {

            scales: {
                y: {
                    beginAtZero: true,
                    max: 100,
                    ticks: {
                        callback: value => value + "%"
                    }
                }
            }

        }

    });

    /* SUMMARY */
    if (report){
        document.getElementById("evaluation-text").innerText = report;
    } else {
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


    if(screen === "history" || screen === "config"){
        document.getElementById("history-screen").style.display = "none";
        document.getElementById("config-panel").style.display = "none";
        document.getElementById("setup-screen").style.display = "block";
    }
    else if(screen === "evaluation"){

        document.getElementById("evaluation-screen").style.display = "none";
        document.getElementById("history-screen").style.display = "block";    
    }

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

            const response = await fetch(`/evaluation-nollm/${interview.session_id}`);
            currentEvaluationSession = interview.session_id;
            const data = await response.json();

            const report = data.report;
            const report_data = data.report_data;

            // hide history
            document.getElementById("history-screen").style.display = "none";

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