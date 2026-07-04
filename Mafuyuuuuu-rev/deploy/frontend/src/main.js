import "./styles.css";

const images = {
  logo: "/assets/nightcord-logo.png",
  mafuyu: "/assets/mafuyu-v2.png",
  profile: "/assets/mafuyu-profile.jpg",
  card: "/assets/mafuyu-card.png",
  chibi: "/assets/mafuyu-charselect.png"
};

const navItems = [
  ["story", "Stories", "ST"],
  ["package", "Packages", "PK"],
  ["archive", "Replay", "RP"],
  ["status", "Status", "OK"]
];

const playlistTracks = [
  {
    title: "Otome Kaibou - Mafuyu solo ver.",
    artist: "Mafuyu Asahina",
    src: "/assets/audio/otome-kaibou-mafuyu-solo.mp3",
    pulse: 0.46
  },
  {
    title: "Jackpot Sad Girl - Mafuyu solo ver.",
    artist: "Mafuyu Asahina",
    src: "/assets/audio/jackpot-sad-girl-mafuyu.mp3",
    pulse: 0.58
  },
  {
    title: "Saisei - Mafuyu solo ver.",
    artist: "Mafuyu Asahina",
    src: "/assets/audio/saisei-mafuyu.mp3",
    pulse: 0.32
  }
];

const starterTemplates = {
  "welcome.tpl": `{% set card_id = call(member(type(System.Guid),NewGuid),now) %}
{% set abs_adapter = member(type(System.Math),Abs) %}
<section style="font-family:system-ui,sans-serif;padding:24px;color:#202339;background:#f8fcff">
  <p style="margin:0 0 6px;color:#5261d8;font-weight:800">Nightcord archive card</p>
  {% if user %}
  <h1 style="margin:0 0 10px">Welcome, {{ user }}</h1>
  {% endif %}
  <p style="margin:0 0 8px">{{ service }} stamped this page at {{ now }}.</p>
  <p style="margin:0 0 8px">Card id: {{ card_id }}</p>
  <p style="margin:0 0 8px">Vocal balance: {{ call(abs_adapter,-25) }}</p>
  <div style="display:flex;gap:6px;flex-wrap:wrap">
  {% for mood in moods %}
    <span style="padding:4px 8px;border:1px solid #d7dcff;border-radius:999px">{{ mood | upper }}</span>
  {% endfor %}
  </div>
</section>`,
  "sekai.tpl": `{% set round_adapter = member(type(System.Math),Round) %}
{% set sqrt_adapter = member(type(System.Math),Sqrt) %}
<section style="font-family:system-ui,sans-serif;padding:24px;color:#202339;background:#fff8fd">
  <p style="margin:0 0 6px;color:#ff6fb4;font-weight:800">SEKAI render pass</p>
  <h1 style="margin:0 0 10px">Story preview for {{ upper user }}</h1>
  <p style="margin:0 0 8px">Adapter: {{ round_adapter }}</p>
  <p style="margin:0 0 8px">Intensity: {{ call(sqrt_adapter,81) }}</p>
  <p style="margin:0">Trace: {{ digest }}</p>
  {% for card in cards %}
    <small style="display:inline-block;margin:8px 6px 0 0;color:#66708f">{{ loop_index }} / {{ card | slug }}</small>
  {% endfor %}
</section>`,
  "nightcord.tpl": `{% set session_id = call(member(type(System.Guid),NewGuid),now) %}
<section style="font-family:system-ui,sans-serif;padding:24px;color:#202339;background:#f7fff9">
  <p style="margin:0 0 6px;color:#18a7ad;font-weight:800">Nightcord queue note</p>
  <h1 style="margin:0 0 10px">{{ service }}</h1>
  <p style="margin:0 0 8px">Clock member: {{ member(type(System.DateTime),UtcNow) }}</p>
  <p style="margin:0 0 8px">Session id: {{ session_id }}</p>
  <p style="margin:0">Desk check: {{ 13 * 25 }}</p>
  {% raw %}<code>{{ archived_expression }}</code>{% endraw %}
</section>`
};

document.querySelector("#app").innerHTML = `
  <div class="sekai-shell">
    <aside class="side-rail">
      <div class="brand-tile">
        <div class="brand-glyph">25</div>
        <div>
          <strong>SEKAI Filing Live</strong>
          <span>Nightcord operations</span>
        </div>
      </div>
      <nav class="rail-nav">
        ${navItems.map(([id, label, mark], index) => `
          <button class="rail-button ${index === 0 ? "active" : ""}" data-screen="${id}" type="button">
            <b>${mark}</b><span>${label}</span>
          </button>
        `).join("")}
      </nav>
      <div class="mix-panel">
        <div class="mix-title"><span>Now playing</span><b id="tempoReadout">132</b></div>
        <div class="track-readout">
          <strong id="trackTitle">${playlistTracks[0].title}</strong>
          <span id="trackArtist">${playlistTracks[0].artist}</span>
        </div>
        <div class="mix-bars">
          ${Array.from({ length: 8 }, (_, index) => `<i style="--i:${index};--h:${0.34 + (index % 4) * 0.16}"></i>`).join("")}
        </div>
        <div class="playlist-controls">
          <button id="prevTrack" type="button">Prev</button>
          <button id="nextTrack" type="button">Next</button>
        </div>
      </div>
      <button class="audio-button" id="audioToggle" type="button">Start audio</button>
      <div class="health-pill" id="health"><i></i><span>checking</span></div>
    </aside>

    <main class="deck">
      <section class="stage-board">
        <canvas id="fxCanvas" class="fx-canvas" aria-hidden="true"></canvas>
        <div class="light-rig" aria-hidden="true">
          ${Array.from({ length: 3 }, (_, index) => `<i style="--i:${index}"></i>`).join("")}
        </div>
        <div class="star-field" aria-hidden="true">
          ${Array.from({ length: 14 }, (_, index) => `<i style="--i:${index};--x:${(index * 37) % 100};--y:${(index * 61) % 100};--s:${0.5 + (index % 5) * 0.17}"></i>`).join("")}
        </div>
        <div class="stage-copy">
          <img class="unit-wordmark" src="${images.logo}" alt="">
          <p>Project SEKAI backstage archive</p>
          <h1>Mafuyu<br><span>Control Deck</span></h1>
          <div class="stage-tags" aria-hidden="true">
            <span>Nightcord</span><span>Archive 25</span><span>132 BPM</span>
          </div>
          <div class="stage-actions">
            <button class="primary-command" data-screen="story" type="button">Open stories</button>
            <button class="ghost-command" data-screen="package" type="button">Prepare package</button>
          </div>
        </div>

        <div class="visual-mixer" aria-hidden="true">
          <div class="disc disc-a"></div>
          <div class="disc disc-b"></div>
          <div class="scanlines"></div>
          <img class="mafuyu-cutout" src="${images.mafuyu}" alt="">
          <div class="album-card album-profile"><img src="${images.profile}" alt=""></div>
          <div class="album-card album-card-art"><img src="${images.card}" alt=""></div>
          <div class="album-card album-chibi"><img src="${images.chibi}" alt=""></div>
        </div>

        <div class="beat-runner" aria-hidden="true">
          ${Array.from({ length: 12 }, (_, index) => `<i style="--d:${index * -0.11}s;--h:${0.25 + (index % 5) * 0.13}"></i>`).join("")}
        </div>
        <div class="lyric-rail" aria-hidden="true">
          <span>Nightcord archive</span><span>story render</span><span>live package</span><span>replay vault</span>
        </div>
      </section>

      <section class="workbench">
        <div class="workbench-head">
          <div>
            <p id="modeEyebrow">Story Cards</p>
            <h2 id="modeTitle">Story compositor</h2>
          </div>
          <div class="top-tabs">
            ${navItems.map(([id, label], index) => `<button class="tab-button ${index === 0 ? "active" : ""}" data-screen="${id}" type="button">${label}</button>`).join("")}
          </div>
        </div>

        <div class="panel active" id="panel-story">
          <div class="editor-grid">
            <form class="control-form" onsubmit="return false">
              <div class="template-strip">
                <button class="template-chip active" data-template="welcome.tpl" type="button">welcome.tpl</button>
                <button class="template-chip" data-template="sekai.tpl" type="button">sekai.tpl</button>
                <button class="template-chip" data-template="nightcord.tpl" type="button">nightcord.tpl</button>
              </div>
              <label>Story file<input id="templateName" value="welcome.tpl" maxlength="80" spellcheck="false"></label>
              <label>Cast<input id="previewUser" value="mafuyu" maxlength="80" spellcheck="false"></label>
              <label>Markup<textarea id="templateBody" spellcheck="false">${starterTemplates["welcome.tpl"]}</textarea></label>
              <div class="button-row">
                <button class="primary-command" id="saveTemplate" type="button">Save story</button>
                <button class="ghost-command" id="previewTemplate" type="button">Render card</button>
              </div>
              <div class="adapter-palette" id="adapterPalette">
                <span>Adapter palette</span>
                <div>loading adapters</div>
              </div>
            </form>
            <div class="preview-phone">
              <div class="phone-bar"><span></span><span></span><span></span></div>
              <iframe id="previewFrame" title="Story preview"></iframe>
            </div>
          </div>
        </div>

        <div class="panel" id="panel-package">
          <div class="editor-grid compact">
            <form class="control-form" onsubmit="return false">
              <label>Package file<input id="exportName" value="daily.txt" maxlength="80" spellcheck="false"></label>
              <label>Encoding<select id="exportFormat"><option value="txt">txt</option><option value="b64">b64</option></select></label>
              <label>Setlist notes<textarea id="exportBody" spellcheck="false">Mafuyu stamped this report.</textarea></label>
              <div class="button-row">
                <button class="primary-command" id="runExport" type="button">Export package</button>
                <a class="ghost-link" id="exportLink" href="/sekai/replays/daily.txt" target="_blank" rel="noreferrer">Open replay</a>
              </div>
            </form>
            <output class="receipt" id="receipt">No package exported.</output>
          </div>
        </div>

        <div class="panel" id="panel-archive">
          <div class="editor-grid compact">
            <form class="control-form short" onsubmit="return false">
              <label>Replay file<input id="archiveName" value="daily.txt" maxlength="80" spellcheck="false"></label>
              <button class="primary-command" id="openArchive" type="button">Load replay</button>
            </form>
            <output class="receipt large" id="archiveBody">No replay loaded.</output>
          </div>
        </div>

        <div class="panel" id="panel-status">
          <div class="status-board">
            <div><span>API</span><b id="metricHealth">...</b></div>
            <div><span>Story route</span><b>Ready</b></div>
            <div><span>Package route</span><b>Ready</b></div>
            <div><span>Replay route</span><b>Ready</b></div>
          </div>
          <div class="signal-grid">
            <form class="control-form short" onsubmit="return false">
              <label>Signal lane<input id="postLane" value="preview" maxlength="40" spellcheck="false"></label>
              <label>Signal memo<textarea id="postMemo" spellcheck="false">Mafuyu stamped this signal.</textarea></label>
              <button class="primary-command" id="sendPost" type="button">Send signal</button>
            </form>
            <output class="receipt" id="postReceipt">No signal sent.</output>
          </div>
        </div>
      </section>
    </main>
  </div>

  <div class="toast" id="toast" role="status" aria-live="polite"></div>
`;

const $ = (id) => document.getElementById(id);
const toast = $("toast");
let toastTimer = 0;
let audioContext = null;
let externalTrack = null;
const trackAvailability = new Map();
let currentTrackIndex = 0;
let masterGain = null;
let musicTimer = 0;
let fxAnimation = 0;
let fxRunning = false;
let fxEnergy = 0;
let musicStep = 0;
let nextStepTime = 0;
let noiseBuffer = null;
let beatTimer = 0;
let pageVisible = true;
let signalCooldownTimer = 0;
const stepTime = 60 / 132 / 2;

const modeText = {
  story: ["Story Cards", "Story compositor"],
  package: ["Live Package", "Setlist exporter"],
  archive: ["Replay Archive", "Archive reader"],
  status: ["Status", "Service monitor"]
};

function notify(message) {
  toast.textContent = message;
  toast.classList.add("show");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => toast.classList.remove("show"), 1800);
}

function safeName(value, fallback) {
  const trimmed = String(value || "").trim();
  return trimmed.length ? trimmed : fallback;
}

function toBase64(value) {
  return btoa(unescape(encodeURIComponent(value)));
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll("\"", "&quot;");
}

function setSignalCooldown(seconds = 2) {
  const button = $("sendPost");
  let remaining = seconds;

  clearInterval(signalCooldownTimer);
  button.disabled = true;
  button.textContent = `Wait ${remaining}s`;

  signalCooldownTimer = setInterval(() => {
    remaining -= 1;
    if (remaining <= 0) {
      clearInterval(signalCooldownTimer);
      signalCooldownTimer = 0;
      button.disabled = false;
      button.textContent = "Send signal";
      return;
    }

    button.textContent = `Wait ${remaining}s`;
  }, 1000);
}

function setScreen(name) {
  const text = modeText[name] || modeText.story;
  $("modeEyebrow").textContent = text[0];
  $("modeTitle").textContent = text[1];

  document.querySelectorAll(".panel").forEach((panel) => panel.classList.toggle("active", panel.id === `panel-${name}`));
  document.querySelectorAll("[data-screen]").forEach((button) => button.classList.toggle("active", button.dataset.screen === name));
}

async function loadAdapters() {
  const host = $("adapterPalette");
  try {
    const res = await fetch("/api/sekai/story-lab/adapters", { cache: "no-store" });
    if (!res.ok) throw new Error("adapter catalog failed");
    const adapters = await res.json();
    host.innerHTML = `
      <span>Adapter palette</span>
      ${adapters.map((item) => {
        const type = item.type || item.Type || "";
        const role = item.role || item.Role || "";
        const members = item.members || item.Members || [];
        return `<div><b>${escapeHtml(type)}</b><em>${escapeHtml(role)}</em><code>${members.map(escapeHtml).join(" / ")}</code></div>`;
      }).join("")}
    `;
  } catch {
    host.innerHTML = "<span>Adapter palette</span><div>unavailable</div>";
  }
}

async function checkHealth() {
  try {
    const res = await fetch("/healthz", { cache: "no-store" });
    if (!res.ok) throw new Error("bad health");
    $("health").className = "health-pill ok";
    $("health").querySelector("span").textContent = "online";
    $("metricHealth").textContent = "Online";
  } catch {
    $("health").className = "health-pill bad";
    $("health").querySelector("span").textContent = "offline";
    $("metricHealth").textContent = "Offline";
  }
}

async function previewTemplate() {
  const name = safeName($("templateName").value, "welcome.tpl");
  const user = safeName($("previewUser").value, "guest");
  const res = await fetch(`/sekai/card-stories/${encodeURIComponent(name)}?user=${encodeURIComponent(user)}`, { cache: "no-store" });
  const text = await res.text();
  if (!res.ok) throw new Error(text || "preview failed");
  $("previewFrame").srcdoc = text;
}

async function saveTemplate() {
  const name = safeName($("templateName").value, "welcome.tpl");
  const res = await fetch(`/api/sekai/card-stories/${encodeURIComponent(name)}`, {
    method: "PUT",
    headers: { "content-type": "text/plain;charset=utf-8" },
    body: $("templateBody").value
  });
  const text = await res.text();
  if (!res.ok) throw new Error(text || "save failed");
  notify("Story saved");
  await previewTemplate();
}

async function exportReport() {
  const name = safeName($("exportName").value, "daily.txt");
  const format = $("exportFormat").value;
  const rawBody = $("exportBody").value;
  const body = format === "b64" ? toBase64(rawBody) : rawBody;
  const res = await fetch("/api/sekai/live-package/import", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ name, format, body })
  });
  const text = await res.text();
  if (!res.ok) throw new Error(text || "export failed");
  $("receipt").textContent = text;
  $("exportLink").href = `/sekai/replays/${encodeURIComponent(name)}`;
  notify("Package exported");
}

async function openArchive() {
  const name = safeName($("archiveName").value, "daily.txt");
  const res = await fetch(`/sekai/replays/${encodeURIComponent(name)}`, { cache: "no-store" });
  const text = await res.text();
  if (!res.ok) throw new Error(text || "not found");
  $("archiveBody").textContent = text;
}

async function sendSignalPost() {
  const category = safeName($("postLane").value, "preview");
  const message = safeName($("postMemo").value, "queued");
  const res = await fetch("/api/desk/posts", {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ category, message })
  });
  const text = await res.text();
  if (res.status === 429) {
    setSignalCooldown(2);
    throw new Error("Signal cooling down");
  }
  if (!res.ok) throw new Error(text || "signal failed");

  const payload = JSON.parse(text);
  $("postReceipt").textContent = JSON.stringify(payload, null, 2);
  setSignalCooldown(2);
  notify("Signal sent");
}

function selectedTrack() {
  return playlistTracks[currentTrackIndex] || playlistTracks[0];
}

function updateTrackReadout() {
  const track = selectedTrack();
  $("trackTitle").textContent = track.title;
  $("trackArtist").textContent = track.artist;
}

function trackIsAvailable(track) {
  if (!trackAvailability.has(track.src)) {
    trackAvailability.set(track.src, fetch(track.src, { method: "HEAD", cache: "no-store" })
      .then((res) => res.ok && String(res.headers.get("content-type") || "").startsWith("audio/"))
      .catch(() => false));
  }
  return trackAvailability.get(track.src);
}

async function prepareExternalTrack() {
  const track = selectedTrack();
  if (!await trackIsAvailable(track)) {
    return false;
  }

  if (!externalTrack) {
    externalTrack = new Audio();
    externalTrack.loop = false;
    externalTrack.preload = "none";
    externalTrack.volume = 0.58;
    externalTrack.addEventListener("ended", () => changeTrack(1, true));
  }

  if (!externalTrack.src.endsWith(track.src)) {
    externalTrack.src = track.src;
    externalTrack.load();
  }
  return true;
}

function initAudio() {
  if (!audioContext) {
    audioContext = new AudioContext();
    masterGain = audioContext.createGain();
    masterGain.gain.value = 0.12;
    masterGain.connect(audioContext.destination);
    noiseBuffer = createNoiseBuffer();
  }
  return audioContext.resume();
}

function createNoiseBuffer() {
  const length = audioContext.sampleRate * 0.25;
  const buffer = audioContext.createBuffer(1, length, audioContext.sampleRate);
  const data = buffer.getChannelData(0);
  for (let i = 0; i < length; i++) {
    data[i] = Math.random() * 2 - 1;
  }
  return buffer;
}

function playTone(frequency, start, duration, type, volume, destination = masterGain) {
  const oscillator = audioContext.createOscillator();
  const gain = audioContext.createGain();
  oscillator.type = type;
  oscillator.frequency.setValueAtTime(frequency, start);
  gain.gain.setValueAtTime(0.0001, start);
  gain.gain.exponentialRampToValueAtTime(volume, start + 0.012);
  gain.gain.exponentialRampToValueAtTime(0.0001, start + duration);
  oscillator.connect(gain);
  gain.connect(destination);
  oscillator.start(start);
  oscillator.stop(start + duration + 0.03);
}

function playKick(start) {
  const oscillator = audioContext.createOscillator();
  const gain = audioContext.createGain();
  oscillator.type = "sine";
  oscillator.frequency.setValueAtTime(118, start);
  oscillator.frequency.exponentialRampToValueAtTime(42, start + 0.16);
  gain.gain.setValueAtTime(0.0001, start);
  gain.gain.exponentialRampToValueAtTime(0.22, start + 0.008);
  gain.gain.exponentialRampToValueAtTime(0.0001, start + 0.24);
  oscillator.connect(gain);
  gain.connect(masterGain);
  oscillator.start(start);
  oscillator.stop(start + 0.26);
}

function playNoise(start, duration, volume, filterFreq) {
  const source = audioContext.createBufferSource();
  const filter = audioContext.createBiquadFilter();
  const gain = audioContext.createGain();
  source.buffer = noiseBuffer;
  filter.type = "highpass";
  filter.frequency.value = filterFreq;
  gain.gain.setValueAtTime(0.0001, start);
  gain.gain.exponentialRampToValueAtTime(volume, start + 0.006);
  gain.gain.exponentialRampToValueAtTime(0.0001, start + duration);
  source.connect(filter);
  filter.connect(gain);
  gain.connect(masterGain);
  source.start(start);
  source.stop(start + duration + 0.02);
}

function playChord(root, start) {
  [0, 4, 7, 11].forEach((semi, index) => {
    playTone(root * Math.pow(2, semi / 12), start + index * 0.012, 0.46, "triangle", 0.035);
  });
}

function scheduleStep(step, start) {
  const bass = [196, 196, 246.94, 220, 174.61, 174.61, 220, 246.94];
  const lead = [392, 493.88, 587.33, 659.25, 587.33, 493.88, 440, 523.25, 659.25, 587.33, 493.88, 392, 440, 493.88, 523.25, 587.33];

  if (step % 4 === 0) playKick(start);
  if (step % 4 === 2) playNoise(start, 0.12, 0.075, 900);
  playNoise(start, 0.035, step % 2 === 0 ? 0.035 : 0.02, 6200);

  if (step % 2 === 0) {
    playTone(bass[(step / 2) % bass.length] / 2, start, 0.24, "sawtooth", 0.045);
  }

  if ([1, 4, 7, 9, 12, 14].includes(step % 16)) {
    playTone(lead[step % lead.length], start, 0.18, "sine", 0.05);
  }

  if (step % 8 === 0) {
    playChord(bass[(step / 2) % bass.length], start);
  }

  fxEnergy = Math.min(1, fxEnergy + (step % 4 === 0 ? 0.72 : 0.34));
  document.documentElement.style.setProperty("--beat", String(Math.min(1, fxEnergy)));
}

function tickMusic() {
  if (!audioContext) return;
  const lookahead = audioContext.currentTime + 0.18;
  while (nextStepTime < lookahead) {
    scheduleStep(musicStep, nextStepTime);
    musicStep = (musicStep + 1) % 32;
    nextStepTime += stepTime;
  }
}

function stopSynth() {
  window.clearInterval(musicTimer);
  musicTimer = 0;
  if (audioContext) {
    audioContext.suspend().catch(() => {});
  }
}

function startBeatPulse(strength = 0.34) {
  window.clearInterval(beatTimer);
  beatTimer = window.setInterval(() => {
    if (!pageVisible) return;
    fxEnergy = Math.min(1, fxEnergy + strength);
    document.documentElement.style.setProperty("--beat", String(Math.min(1, fxEnergy)));
  }, 228);
}

function stopBeatPulse() {
  window.clearInterval(beatTimer);
  beatTimer = 0;
}

async function startFallbackSynth() {
  await initAudio();
  nextStepTime = audioContext.currentTime + 0.05;
  tickMusic();
  musicTimer = window.setInterval(tickMusic, 120);
  startBeatPulse(0.22);
}

async function startAudio(autoStart = false) {
  stopBeatPulse();
  stopSynth();
  if (externalTrack) externalTrack.pause();
  document.body.classList.add("audio-on");
  $("audioToggle").classList.add("active");
  $("audioToggle").textContent = "Stop audio";

  if (await prepareExternalTrack()) {
    try {
      externalTrack.currentTime = externalTrack.currentTime || 0;
      await externalTrack.play();
      startBeatPulse(selectedTrack().pulse);
      return true;
    } catch {
      if (!autoStart) notify("Browser blocked audio playback");
    }
  }

  if (externalTrack) {
    externalTrack.pause();
  }

  try {
    await startFallbackSynth();
    return true;
  } catch {
    stopAudioUi();
    if (!autoStart) notify("Audio needs a click");
    return false;
  }
}

async function toggleAudio() {
  if (document.body.classList.contains("audio-on")) {
    stopAudioUi();
    return;
  }
  await startAudio(false);
}

function stopAudioUi() {
  document.body.classList.remove("audio-on");
  $("audioToggle").classList.remove("active");
  $("audioToggle").textContent = "Start audio";
  stopBeatPulse();
  stopSynth();
  if (externalTrack) {
    externalTrack.pause();
  }
}

async function changeTrack(delta, autoplay = document.body.classList.contains("audio-on")) {
  currentTrackIndex = (currentTrackIndex + delta + playlistTracks.length) % playlistTracks.length;
  updateTrackReadout();
  if (externalTrack) {
    externalTrack.pause();
    externalTrack.removeAttribute("src");
    externalTrack.load();
  }
  if (autoplay) {
    await startAudio(false);
  }
}

document.addEventListener("visibilitychange", () => {
  pageVisible = !document.hidden;
  if (!pageVisible && document.body.classList.contains("audio-on")) {
    stopAudioUi();
  }
});

function initFx() {
  if (fxRunning) return;
  fxRunning = true;
  const canvas = $("fxCanvas");
  const ctx = canvas.getContext("2d");
  const particles = [];
  const colors = ["#28a8ff", "#18d6df", "#ff6fb4", "#826dff", "#ffd45c"];
  let lastFrame = 0;

  function resize() {
    const rect = canvas.getBoundingClientRect();
    const dpr = Math.min(window.devicePixelRatio || 1, 1.35);
    canvas.width = Math.max(1, Math.floor(rect.width * dpr));
    canvas.height = Math.max(1, Math.floor(rect.height * dpr));
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  }

  function spawn(width, height, boost = 0) {
    particles.push({
      x: Math.random() * width,
      y: height + 20 + Math.random() * 90,
      vx: (Math.random() - 0.5) * 0.55,
      vy: -0.72 - Math.random() * 1.6 - boost,
      size: 4 + Math.random() * 10 + boost * 6,
      color: colors[Math.floor(Math.random() * colors.length)],
      spin: Math.random() * Math.PI,
      rot: (Math.random() - 0.5) * 0.08,
      alpha: 0.28 + Math.random() * 0.42
    });
  }

  function frame(time = 0) {
    if (!pageVisible) {
      fxAnimation = requestAnimationFrame(frame);
      return;
    }

    if (time - lastFrame < 33) {
      fxAnimation = requestAnimationFrame(frame);
      return;
    }
    lastFrame = time;

    const width = canvas.clientWidth;
    const height = canvas.clientHeight;
    ctx.clearRect(0, 0, width, height);

    const target = document.body.classList.contains("audio-on") ? 16 : 8;
    while (particles.length < target) spawn(width, height, fxEnergy);
    if (fxEnergy > 0.52) {
      for (let i = 0; i < 2; i++) spawn(width, height, fxEnergy);
    }

    for (let i = particles.length - 1; i >= 0; i--) {
      const p = particles[i];
      p.x += p.vx;
      p.y += p.vy * (document.body.classList.contains("audio-on") ? 1.45 : 1);
      p.spin += p.rot;
      p.alpha *= 0.996;

      ctx.save();
      ctx.translate(p.x, p.y);
      ctx.rotate(p.spin);
      ctx.globalAlpha = p.alpha;
      ctx.fillStyle = p.color;
      ctx.shadowColor = p.color;
      ctx.shadowBlur = 10;
      ctx.fillRect(-p.size * 0.5, -p.size * 0.18, p.size, p.size * 0.36);
      ctx.restore();

      if (p.y < -40 || p.alpha < 0.08) particles.splice(i, 1);
    }
    fxEnergy *= 0.9;
    document.documentElement.style.setProperty("--beat", String(fxEnergy.toFixed(3)));
    fxAnimation = requestAnimationFrame(frame);
  }

  resize();
  window.addEventListener("resize", resize);
  fxAnimation = requestAnimationFrame(frame);
}

let pointerFrame = 0;
let pointerEvent = null;

document.addEventListener("pointermove", (event) => {
  pointerEvent = event;
  if (pointerFrame) return;

  pointerFrame = requestAnimationFrame(() => {
    pointerFrame = 0;
    const board = document.querySelector(".stage-board");
    if (!board || !pointerEvent) return;
    const rect = board.getBoundingClientRect();
    const x = ((pointerEvent.clientX - rect.left) / rect.width - 0.5).toFixed(3);
    const y = ((pointerEvent.clientY - rect.top) / rect.height - 0.5).toFixed(3);
    board.style.setProperty("--mx", x);
    board.style.setProperty("--my", y);
  });
});

document.addEventListener("pointerleave", () => {
  const board = document.querySelector(".stage-board");
  if (!board) return;
  board.style.setProperty("--mx", "0");
  board.style.setProperty("--my", "0");
});

document.querySelectorAll("[data-screen]").forEach((button) => button.addEventListener("click", () => setScreen(button.dataset.screen)));
document.querySelectorAll(".template-chip").forEach((button) => button.addEventListener("click", () => {
  $("templateName").value = button.dataset.template;
  if (starterTemplates[button.dataset.template]) {
    $("templateBody").value = starterTemplates[button.dataset.template];
  }
  document.querySelectorAll(".template-chip").forEach((item) => item.classList.toggle("active", item === button));
}));

$("audioToggle").addEventListener("click", toggleAudio);
$("prevTrack").addEventListener("click", () => changeTrack(-1).catch((err) => notify(err.message || String(err))));
$("nextTrack").addEventListener("click", () => changeTrack(1).catch((err) => notify(err.message || String(err))));
$("saveTemplate").addEventListener("click", () => saveTemplate().catch((err) => notify(err.message || String(err))));
$("previewTemplate").addEventListener("click", () => previewTemplate().catch((err) => notify(err.message || String(err))));
$("runExport").addEventListener("click", () => exportReport().catch((err) => notify(err.message || String(err))));
$("openArchive").addEventListener("click", () => openArchive().catch((err) => notify(err.message || String(err))));
$("sendPost").addEventListener("click", () => sendSignalPost().catch((err) => notify(err.message || String(err))));
$("exportName").addEventListener("input", () => {
  $("exportLink").href = `/sekai/replays/${encodeURIComponent(safeName($("exportName").value, "daily.txt"))}`;
});

setScreen("story");
updateTrackReadout();
initFx();
loadAdapters().catch(() => {});
checkHealth();
previewTemplate().catch(() => {});
window.setTimeout(() => startAudio(true).catch(() => stopAudioUi()), 450);
setInterval(checkHealth, 5000);
