// Backend configuration (update BACKEND_PORT if your API runs on a different port)
const BACKEND_HOST = window.location.hostname || "localhost";
const BACKEND_PORT = "8000"; // change this if your FastAPI server is on another port

const HTTP_PROTOCOL = window.location.protocol === "https:" ? "https:" : "http:";
const WS_PROTOCOL = HTTP_PROTOCOL === "https:" ? "wss:" : "ws:";

const BASE_HTTP_URL = `${HTTP_PROTOCOL}//${BACKEND_HOST}:${BACKEND_PORT}`;
const BASE_WS_URL = `${WS_PROTOCOL}//${BACKEND_HOST}:${BACKEND_PORT}`;

const WS_URL = `${BASE_WS_URL}/ws/live`;
const VIDEO_URL = `${BASE_HTTP_URL}/api/video`;
const API_URL = `${BASE_HTTP_URL}/api`;

// DOM Elements
const bodyEl = document.body;
const valPeople = document.getElementById("val-people");
const valDensity = document.getElementById("val-density");
const valRisk = document.getElementById("val-risk");
const valUptime = document.getElementById("val-uptime");

const videoStreamEl = document.getElementById("video-stream");
const playbackControls = document.getElementById("playback-controls");

// Buttons & Inputs
const btnStartCamera = document.getElementById("btn-start-camera");
const btnToggleHeatmap = document.getElementById("btn-toggle-heatmap");
const btnPlayPause = document.getElementById("btn-play-pause");
const iconPlay = document.getElementById("icon-play");
const iconPause = document.getElementById("icon-pause");
const seekSlider = document.getElementById("seek-slider");
const progressText = document.getElementById("progress-text");

// Upload Modal
const modalUpload = document.getElementById("upload-modal");
const btnOpenUploads = document.querySelectorAll("#btn-open-upload");
const btnCloseUpload = document.getElementById("btn-close-upload");
const fileInput = document.getElementById("file-input");
const fileNameDisplay = document.getElementById("file-name-display");
const btnSubmitUpload = document.getElementById("btn-submit-upload");
const btnFakeBrowse = document.getElementById("btn-fake-browse");
const uploadStatusText = document.getElementById("upload-status-text");

// State
let currentPeopleCount = 0;
let currentRisk = "NORMAL";
let isHeatmapActive = false;
let isPaused = false; // Fixed False to false
let isDraggingSlider = false;
let ws = null;
let uptimeSeconds = 0;

// Force video stream off by default unless clicked
videoStreamEl.src = ""; // Clear src initially

// Setup Uptime Timer
setInterval(() => {
    uptimeSeconds++;
    const m = Math.floor(uptimeSeconds / 60).toString().padStart(2, "0");
    const s = (uptimeSeconds % 60).toString().padStart(2, "0");
    valUptime.textContent = `${m}:${s}`;
}, 1000);

// Initialize WebSocket
function connectWebSocket() {
    ws = new WebSocket(WS_URL);

    ws.onmessage = (event) => {
        try {
            const data = JSON.parse(event.data);

            if (data.status === "Initializing...") return;

            if (data.source === "off") {
                // Do nothing
                valRisk.textContent = "Standby";
                return;
            }

            if (data.total_people !== undefined) {
                updateDashboard(data);

                // Show playback controls ONLY if it's a video file uploaded
                if (data.source === "video") {
                    playbackControls.style.display = "flex";
                    // Update slider unless user is holding it
                    if (!isDraggingSlider && data.progress_pct !== undefined) {
                        seekSlider.value = data.progress_pct;
                        progressText.textContent = Math.round(data.progress_pct) + "%";
                    }
                } else {
                    playbackControls.style.display = "none";
                }

                // Update Play/pause icons
                isPaused = data.paused;
                if (isPaused) {
                    iconPause.style.display = "none";
                    iconPlay.style.display = "block";
                } else {
                    iconPlay.style.display = "none";
                    iconPause.style.display = "block";
                }
            }
        } catch (e) {
            console.error("Error:", e);
        }
    };

    ws.onerror = () => { valRisk.textContent = "Error"; };
    ws.onclose = () => { setTimeout(connectWebSocket, 3000); };
}

function updateDashboard(data) {
    const newPeople = data.total_people;
    if (newPeople !== currentPeopleCount) {
        animateNumberChange(valPeople, currentPeopleCount, newPeople);
        currentPeopleCount = newPeople;
    }

    const backendRisk = data.risk_level || "NORMAL";
    let displayRisk = "Safe";
    let themeRisk = backendRisk;

    if (backendRisk === "WARNING") displayRisk = "Alert";
    if (backendRisk === "CRITICAL") displayRisk = "Critical";

    let densityLevel = "Low";
    if (backendRisk === "WARNING") densityLevel = "Medium";
    if (backendRisk === "CRITICAL") densityLevel = "High";

    const emergencyTitle = document.getElementById("emergency-title");
    const emergencyDesc = document.getElementById("emergency-desc");

    // Weapon Override
    if (data.threat_detected) {
        displayRisk = "WEAPON DETECTED";
        themeRisk = "WEAPON-THREAT";
        emergencyTitle.textContent = "WEAPON DETECTED";
        emergencyDesc.textContent = `Security Alert! ${data.total_threats} threat(s) found. Highest severity: ${data.highest_severity}`;

        // If density was low, force Critical display so the user knows to look at the screen
        densityLevel = "High Risk";
    } else {
        // Reset emergency text back to density
        emergencyTitle.textContent = "EMERGENCY PROTOCOL ACTIVATED";
        emergencyDesc.textContent = "Critical density detected! Area per person is dangerously low.";
    }

    if (themeRisk !== currentRisk) {
        changeTheme(themeRisk);
        currentRisk = themeRisk;
    }

    valRisk.textContent = displayRisk;
    valDensity.textContent = densityLevel;
}

function changeTheme(riskLevel) {
    bodyEl.classList.remove('theme-normal', 'theme-warning', 'theme-critical', 'theme-weapon-threat');
    bodyEl.classList.add(`theme-${riskLevel.toLowerCase()}`);
}

function animateNumberChange(element, oldVal, newVal) {
    element.textContent = newVal;
    element.classList.remove('number-up', 'number-down');
    void element.offsetWidth; // trigger reflow
    if (newVal > oldVal) element.classList.add('number-up');
    else if (newVal < oldVal) element.classList.add('number-down');
}

// ========================
// Button Actions & API calls
// ========================

let isCameraOn = false;

btnStartCamera.addEventListener("click", async () => {
    if (!isCameraOn) {
        try {
            await fetch(`${API_URL}/start-camera`, { method: "POST" });
            videoStreamEl.src = VIDEO_URL + "?" + new Date().getTime(); // Reload image stream
            isCameraOn = true;
            btnStartCamera.innerHTML = `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18.36 6.64a9 9 0 1 1-12.73 0"></path><line x1="12" y1="2" x2="12" y2="12"></line></svg> Turn Off Camera`;
            btnStartCamera.style.backgroundColor = 'var(--color-critical)';
        } catch (e) {
            alert("Failed to start camera");
        }
    } else {
        try {
            await fetch(`${API_URL}/stop-camera`, { method: "POST" });
            isCameraOn = false;
            btnStartCamera.innerHTML = `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"/><circle cx="12" cy="13" r="4"/></svg> Open Camera`;
            btnStartCamera.style.backgroundColor = ''; // Reset to default
        } catch (e) {
            alert("Failed to stop camera");
        }
    }
});

btnToggleHeatmap.addEventListener("click", async () => {
    isHeatmapActive = !isHeatmapActive;
    if (isHeatmapActive) btnToggleHeatmap.classList.add("active");
    else btnToggleHeatmap.classList.remove("active");

    await fetch(`${API_URL}/heatmap-toggle`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ enabled: isHeatmapActive })
    });
});

// Playback Control UI overrides
btnPlayPause.addEventListener("click", async () => {
    const desiredAction = isPaused ? "play" : "pause";
    await fetch(`${API_URL}/video-control`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: desiredAction })
    });
});

// Slider scrubbing
seekSlider.addEventListener("mousedown", () => isDraggingSlider = true);
seekSlider.addEventListener("mouseup", () => isDraggingSlider = false);
seekSlider.addEventListener("input", () => progressText.textContent = seekSlider.value + "%");
seekSlider.addEventListener("change", async () => {
    const val = parseFloat(seekSlider.value) / 100.0;
    await fetch(`${API_URL}/video-control`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "seek", value: val })
    });
});


// Upload Logic
btnOpenUploads.forEach(btn => btn.addEventListener("click", (e) => {
    e.preventDefault();
    modalUpload.classList.add("open");
}));
btnCloseUpload.addEventListener("click", () => modalUpload.classList.remove("open"));

if (btnFakeBrowse) {
    btnFakeBrowse.addEventListener("click", () => {
        fileInput.click();
    });
}

fileInput.addEventListener("change", (e) => {
    if (e.target.files.length > 0) {
        fileNameDisplay.textContent = e.target.files[0].name;
        btnSubmitUpload.disabled = false;
        uploadStatusText.textContent = "Ready to upload.";
    }
});

btnSubmitUpload.addEventListener("click", async () => {
    if (fileInput.files.length === 0) return;

    btnSubmitUpload.disabled = true;
    btnSubmitUpload.textContent = "Uploading...";

    const formData = new FormData();
    formData.append("file", fileInput.files[0]);

    try {
        const res = await fetch(`${API_URL}/upload`, {
            method: "POST",
            body: formData
        });
        if (res.ok) {
            uploadStatusText.textContent = "Upload successful!";
            videoStreamEl.src = VIDEO_URL + "?" + new Date().getTime(); // Reload stream
            setTimeout(() => { modalUpload.classList.remove("open"); btnSubmitUpload.textContent = "Upload"; btnSubmitUpload.disabled = false; }, 1000);
        }
    } catch (e) {
        uploadStatusText.textContent = "Upload failed.";
        btnSubmitUpload.textContent = "Upload";
        btnSubmitUpload.disabled = false;
    }
});

// Start
document.addEventListener("DOMContentLoaded", () => {
    connectWebSocket();
});
