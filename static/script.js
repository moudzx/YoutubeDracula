const urlInput = document.getElementById("url");
const fetchBtn = document.getElementById("fetchBtn");
const fetchHint = document.getElementById("fetchHint");
const featuresNote = document.getElementById("featuresNote");

// --- single video elements ---
const videoPanel = document.getElementById("videoPanel");
const thumb = document.getElementById("thumb");
const videoTitle = document.getElementById("videoTitle");
const videoUploader = document.getElementById("videoUploader");
const videoDuration = document.getElementById("videoDuration");

const videoModeTabs = document.getElementById("videoModeTabs");
const formatSelect = document.getElementById("formatSelect");
const mp3Row = document.getElementById("mp3Row");
const convertMp3 = document.getElementById("convertMp3");

const sectionToggle = document.getElementById("sectionToggle");
const sectionBlock = document.getElementById("sectionBlock");
const rangeStart = document.getElementById("rangeStart");
const rangeEnd = document.getElementById("rangeEnd");
const startTime = document.getElementById("startTime");
const endTime = document.getElementById("endTime");

const downloadBtn = document.getElementById("downloadBtn");
const progressWrap = document.getElementById("progressWrap");
const progressLabel = document.getElementById("progressLabel");
const progressFill = document.getElementById("progressFill");

// --- playlist elements ---
const playlistPanel = document.getElementById("playlistPanel");
const playlistTitle = document.getElementById("playlistTitle");
const playlistCount = document.getElementById("playlistCount");
const trackList = document.getElementById("trackList");
const playlistModeTabs = document.getElementById("playlistModeTabs");
const playlistAudioFormatBlock = document.getElementById("playlistAudioFormatBlock");
const playlistVideoQualityBlock = document.getElementById("playlistVideoQualityBlock");
const playlistAudioFormat = document.getElementById("playlistAudioFormat");
const playlistVideoQuality = document.getElementById("playlistVideoQuality");
const playlistModeHint = document.getElementById("playlistModeHint");
const playlistDownloadBtn = document.getElementById("playlistDownloadBtn");
const playlistProgressWrap = document.getElementById("playlistProgressWrap");
const playlistProgressLabel = document.getElementById("playlistProgressLabel");
const playlistProgressFill = document.getElementById("playlistProgressFill");

let currentDuration = 0;
let currentFormats = [];
let currentVideoMode = "video"; // "video" | "audio"
let currentPlaylistUrl = "";
let currentPlaylistTitle = "";
let currentPlaylistMode = "stitch"; // "stitch" | "stitch_video" | "separate_audio" | "separate_video"

// ---------- helpers ----------

function secondsToHHMMSS(sec) {
  sec = Math.round(sec);
  const h = Math.floor(sec / 3600);
  const m = Math.floor((sec % 3600) / 60);
  const s = sec % 60;
  return [h, m, s].map(v => String(v).padStart(2, "0")).join(":");
}

function hhmmssToSeconds(t) {
  if (!t || !t.trim()) return null;
  const parts = t.split(":").map(Number);
  while (parts.length < 3) parts.unshift(0);
  const [h, m, s] = parts;
  return h * 3600 + m * 60 + s;
}

function formatDuration(sec) {
  if (!sec) return "";
  return `Duration: ${secondsToHHMMSS(sec)}`;
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}

function setActiveTab(container, mode) {
  container.querySelectorAll(".mode-tab").forEach(btn => {
    btn.classList.toggle("active", btn.dataset.mode === mode);
  });
}

// ---------- single video: mode tabs (Video / Audio only) ----------

videoModeTabs.addEventListener("click", (e) => {
  const btn = e.target.closest(".mode-tab");
  if (!btn) return;
  currentVideoMode = btn.dataset.mode;
  setActiveTab(videoModeTabs, currentVideoMode);
  populateFormats(currentFormats);
});

function populateFormats(formats) {
  const filtered = formats.filter(f =>
    currentVideoMode === "audio" ? f.is_audio_only : !f.is_audio_only
  );

  formatSelect.innerHTML = "";
  filtered.forEach((f, idx) => {
    const opt = document.createElement("option");
    opt.value = formats.indexOf(f);
    const size = f.filesize_mb ? ` (~${f.filesize_mb} MB)` : "";
    opt.textContent = `${f.label}${size} — .${f.ext}`;
    formatSelect.appendChild(opt);
  });

  mp3Row.classList.toggle("hidden", currentVideoMode !== "audio");
  downloadBtn.textContent = currentVideoMode === "audio" ? "Download audio" : "Download video";
}

// ---------- single video: section toggle ----------

sectionToggle.addEventListener("change", () => {
  sectionBlock.classList.toggle("hidden", !sectionToggle.checked);
  if (!sectionToggle.checked) {
    rangeStart.value = 0;
    rangeEnd.value = 100;
    startTime.value = "00:00:00";
    endTime.value = "";
  }
});

rangeStart.addEventListener("input", () => {
  if (parseInt(rangeStart.value) > parseInt(rangeEnd.value)) {
    rangeStart.value = rangeEnd.value;
  }
  const sec = (rangeStart.value / 100) * currentDuration;
  startTime.value = secondsToHHMMSS(sec);
});

rangeEnd.addEventListener("input", () => {
  if (parseInt(rangeEnd.value) < parseInt(rangeStart.value)) {
    rangeEnd.value = rangeStart.value;
  }
  const sec = (rangeEnd.value / 100) * currentDuration;
  endTime.value = secondsToHHMMSS(sec);
});

startTime.addEventListener("change", () => {
  const sec = hhmmssToSeconds(startTime.value) || 0;
  rangeStart.value = currentDuration ? (sec / currentDuration) * 100 : 0;
});

endTime.addEventListener("change", () => {
  const sec = hhmmssToSeconds(endTime.value);
  if (sec != null && currentDuration) {
    rangeEnd.value = (sec / currentDuration) * 100;
  }
});

// ---------- Load button ----------

fetchBtn.addEventListener("click", async () => {
  const url = urlInput.value.trim();
  if (!url) return;

  fetchBtn.disabled = true;
  fetchBtn.textContent = "Loading…";
  fetchHint.textContent = "Fetching info…";
  fetchHint.style.color = "";
  videoPanel.classList.add("hidden");
  playlistPanel.classList.add("hidden");

  try {
    const res = await fetch("/api/info", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url }),
    });
    const data = await res.json();

    if (!res.ok) {
      fetchHint.textContent = data.error || "Something went wrong fetching that.";
      fetchHint.style.color = "var(--danger)";
      return;
    }

    if (data.is_playlist) {
      renderPlaylist(url, data);
      featuresNote.classList.add("hidden");
      fetchHint.textContent = "Only use this on videos you have the rights to download.";
      return;
    }

    currentDuration = data.duration || 0;
    currentFormats = data.formats || [];
    currentVideoMode = "video";
    setActiveTab(videoModeTabs, "video");

    thumb.src = data.thumbnail || "";
    videoTitle.textContent = data.title || "Untitled video";
    videoUploader.textContent = data.uploader || "";
    videoDuration.textContent = formatDuration(currentDuration);

    sectionToggle.checked = false;
    sectionBlock.classList.add("hidden");
    rangeStart.value = 0;
    rangeEnd.value = 100;
    startTime.value = "00:00:00";
    endTime.value = "";

    populateFormats(currentFormats);

    videoPanel.classList.remove("hidden");
    featuresNote.classList.add("hidden");
    fetchHint.textContent = "Only use this on videos you have the rights to download.";
  } catch (err) {
    fetchHint.textContent = "Network error — check the URL and try again.";
    fetchHint.style.color = "var(--danger)";
  } finally {
    fetchBtn.disabled = false;
    fetchBtn.textContent = "Load";
  }
});

// ---------- single video: download ----------

downloadBtn.addEventListener("click", async () => {
  const url = urlInput.value.trim();
  const f = currentFormats[formatSelect.value];
  if (!url || !f) return;

  const useSection = sectionToggle.checked;
  const start = useSection ? startTime.value.trim() : "";
  const end = useSection ? endTime.value.trim() : "";

  downloadBtn.disabled = true;
  downloadBtn.textContent = "Working…";
  progressWrap.classList.remove("hidden");
  progressLabel.textContent = "Starting…";
  progressFill.style.width = "2%";

  try {
    const res = await fetch("/api/download", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        url,
        format_id: f.format_id,
        is_audio_only: f.is_audio_only,
        convert_mp3: f.is_audio_only && convertMp3.checked,
        start_time: start,
        end_time: end,
      }),
    });
    const data = await res.json();

    if (!res.ok) {
      progressLabel.textContent = data.error || "Could not start download.";
      resetDownloadBtn();
      return;
    }

    pollJob(data.job_id);
  } catch (err) {
    progressLabel.textContent = "Network error starting download.";
    resetDownloadBtn();
  }
});

function resetDownloadBtn() {
  downloadBtn.disabled = false;
  downloadBtn.textContent = currentVideoMode === "audio" ? "Download audio" : "Download video";
}

async function pollJob(jobId) {
  const poll = setInterval(async () => {
    try {
      const res = await fetch(`/api/status/${jobId}`);
      const data = await res.json();

      if (data.status === "downloading") {
        progressLabel.textContent = `Downloading… ${data.progress || ""}`;
        const pct = parseFloat((data.progress || "0").replace("%", "")) || 5;
        progressFill.style.width = Math.max(pct, 5) + "%";
      } else if (data.status === "done") {
        clearInterval(poll);
        progressLabel.textContent = "Done — preparing your file…";
        progressFill.style.width = "100%";
        window.location.href = `/api/file/${jobId}`;
        setTimeout(() => {
          progressLabel.textContent = "Downloaded. Ready for another one?";
          resetDownloadBtn();
        }, 1500);
      } else if (data.status === "error") {
        clearInterval(poll);
        progressLabel.textContent = `Error: ${data.error}`;
        resetDownloadBtn();
      }
    } catch (err) {
      clearInterval(poll);
      progressLabel.textContent = "Lost connection while downloading.";
      resetDownloadBtn();
    }
  }, 1200);
}

// ---------- playlist: render + mode tabs ----------

function renderPlaylist(url, data) {
  currentPlaylistUrl = url;
  currentPlaylistTitle = data.playlist_title || "Playlist";
  currentPlaylistMode = "stitch";
  setActiveTab(playlistModeTabs, "stitch");

  playlistTitle.textContent = currentPlaylistTitle;
  playlistCount.textContent = `${data.count} track${data.count === 1 ? "" : "s"}`;

  trackList.innerHTML = "";
  data.tracks.forEach((t, i) => {
    const row = document.createElement("div");
    row.className = "track-row-item";
    const dur = t.duration ? secondsToHHMMSS(t.duration) : "";
    row.innerHTML = `
      <span class="track-num">${i + 1}</span>
      <span class="track-name">${escapeHtml(t.title)}</span>
      <span class="track-dur">${dur}</span>
    `;
    trackList.appendChild(row);
  });

  updatePlaylistModeUI();
  playlistProgressWrap.classList.add("hidden");
  playlistDownloadBtn.disabled = false;
  playlistPanel.classList.remove("hidden");
}

playlistModeTabs.addEventListener("click", (e) => {
  const btn = e.target.closest(".mode-tab");
  if (!btn) return;
  currentPlaylistMode = btn.dataset.mode;
  setActiveTab(playlistModeTabs, currentPlaylistMode);
  updatePlaylistModeUI();
});

function updatePlaylistModeUI() {
  const isVideo = currentPlaylistMode === "separate_video" || currentPlaylistMode === "stitch_video";
  playlistAudioFormatBlock.classList.toggle("hidden", isVideo);
  playlistVideoQualityBlock.classList.toggle("hidden", !isVideo);

  if (currentPlaylistMode === "stitch") {
    playlistModeHint.textContent = "All tracks download and merge into a single audio file, in order.";
    playlistDownloadBtn.textContent = `Download combined ${playlistAudioFormat.value.toUpperCase()}`;
  } else if (currentPlaylistMode === "stitch_video") {
    playlistModeHint.textContent = "All tracks download as video and stitch into one MP4, in order. Larger playlists take longer since every track re-encodes to a consistent format.";
    playlistDownloadBtn.textContent = "Download combined video (.mp4)";
  } else if (currentPlaylistMode === "separate_audio") {
    playlistModeHint.textContent = "Each track downloads as its own audio file, delivered as a .zip.";
    playlistDownloadBtn.textContent = "Download audio files (.zip)";
  } else {
    playlistModeHint.textContent = "Each track downloads as its own video file, delivered as a .zip.";
    playlistDownloadBtn.textContent = "Download video files (.zip)";
  }
}

playlistAudioFormat.addEventListener("change", updatePlaylistModeUI);

// ---------- playlist: download ----------

playlistDownloadBtn.addEventListener("click", async () => {
  if (!currentPlaylistUrl) return;

  playlistDownloadBtn.disabled = true;
  const workingLabel = "Working…";
  playlistDownloadBtn.textContent = workingLabel;
  playlistProgressWrap.classList.remove("hidden");
  playlistProgressLabel.textContent = "Starting…";
  playlistProgressFill.style.width = "2%";

  const body = {
    url: currentPlaylistUrl,
    playlist_title: currentPlaylistTitle,
    mode: currentPlaylistMode,
  };
  if (currentPlaylistMode === "separate_video" || currentPlaylistMode === "stitch_video") {
    body.format = playlistVideoQuality.value;
  } else {
    body.format = playlistAudioFormat.value;
  }

  try {
    const res = await fetch("/api/download_playlist", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const data = await res.json();

    if (!res.ok) {
      playlistProgressLabel.textContent = data.error || "Could not start download.";
      resetPlaylistBtn();
      return;
    }

    pollPlaylistJob(data.job_id);
  } catch (err) {
    playlistProgressLabel.textContent = "Network error starting download.";
    resetPlaylistBtn();
  }
});

function resetPlaylistBtn() {
  playlistDownloadBtn.disabled = false;
  updatePlaylistModeUI();
}

async function pollPlaylistJob(jobId) {
  const poll = setInterval(async () => {
    try {
      const res = await fetch(`/api/status/${jobId}`);
      const data = await res.json();

      if (data.status === "done") {
        clearInterval(poll);
        playlistProgressLabel.textContent = "Done — preparing your file…";
        playlistProgressFill.style.width = "100%";
        window.location.href = `/api/file/${jobId}`;
        setTimeout(() => {
          playlistProgressLabel.textContent = "Downloaded. Ready for another one?";
          resetPlaylistBtn();
        }, 1500);
      } else if (data.status === "error") {
        clearInterval(poll);
        playlistProgressLabel.textContent = `Error: ${data.error}`;
        resetPlaylistBtn();
      } else if (data.progress === "stitching") {
        playlistProgressLabel.textContent = "Stitching tracks into one file…";
        playlistProgressFill.style.width = "95%";
      } else if (data.progress === "zipping") {
        playlistProgressLabel.textContent = "Zipping up the files…";
        playlistProgressFill.style.width = "95%";
      } else if (data.status === "downloading") {
        const total = data.total_tracks || 0;
        const current = data.current_track || 0;
        const trackLabel = total ? `Track ${current}/${total}` : `Track ${current}`;
        playlistProgressLabel.textContent = `${trackLabel} — ${data.progress || ""}`;
        const pct = total ? (current / total) * 100 : 5;
        playlistProgressFill.style.width = Math.max(pct, 5) + "%";
      }
    } catch (err) {
      clearInterval(poll);
      playlistProgressLabel.textContent = "Lost connection while downloading.";
      resetPlaylistBtn();
    }
  }, 1200);
}
