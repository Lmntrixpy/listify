function getPreferredTheme() {
  const saved = localStorage.getItem("theme"); // "light" | "dark" | null
  if (saved === "light" || saved === "dark") return saved;

  const prefersDark = window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches;
  return prefersDark ? "dark" : "light";
}

function applyTheme(theme) {
  document.documentElement.setAttribute("data-theme", theme);
}

function toggleTheme() {
  const current = document.documentElement.getAttribute("data-theme") || getPreferredTheme();
  const next = current === "dark" ? "light" : "dark";
  localStorage.setItem("theme", next);
  applyTheme(next);
}

function updateTimeRangeState() {
  const sourceEl = document.getElementById("source");
  const timeRange = document.getElementById("time_range");
  const desc = document.getElementById("description");
  const allBtn = document.getElementById("allSongsBtn");

  if (!sourceEl || !timeRange) return;

  if (sourceEl.value === "liked") {
    timeRange.disabled = true;
    timeRange.style.opacity = "0.6";
    timeRange.title = "Zeitraum ist nur bei Top Tracks relevant.";

    if (allBtn) {
      allBtn.disabled = false;
      allBtn.style.opacity = "1";
    }

    if (desc && desc.value.trim() === "Automatisch erstellt aus meinen Spotify Top Tracks") {
      desc.value = "Automatisch erstellt aus meinen Lieblingssongs";
    }
  } else {
    timeRange.disabled = false;
    timeRange.style.opacity = "1";
    timeRange.title = "";

    if (allBtn) {
      allBtn.disabled = true;
      allBtn.style.opacity = "0.6";
    }

    if (desc && desc.value.trim() === "Automatisch erstellt aus meinen Spotify Liked Songs") {
      desc.value = "Automatisch erstellt aus meinen Spotify Top Tracks";
    }
  }
}

async function createPlaylist() {
  const statusEl = document.getElementById("status");
  const btn = document.getElementById("createBtn");
  if (statusEl) statusEl.textContent = "Arbeite ...";
  if (btn) btn.disabled = true;

  try {
    const body = {
      source: document.getElementById("source").value,
      time_range: document.getElementById("time_range").value,
      limit: Number(document.getElementById("limit").value),
      name: document.getElementById("name").value,
      description: document.getElementById("description").value,
      public: document.getElementById("public").value === "true",
    };

    const res = await fetch("/api/create_playlist", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });

    const data = await res.json().catch(() => ({}));

    if (!res.ok) {
      if (statusEl) statusEl.textContent = "Fehler:\n" + JSON.stringify(data, null, 2);
      return;
    }

    let msg =
      `OK\n` +
      `Tracks hinzugefügt: ${data.tracks_added}\n` +
      `Playlist ID: ${data.playlist_id}`;
    if (data.playlist_url) msg += `\nLink: ${data.playlist_url}`;
    if (statusEl) statusEl.textContent = msg;
  } finally {
    if (btn) btn.disabled = false;
  }
}

document.addEventListener("DOMContentLoaded", () => {
  // Theme init
  applyTheme(getPreferredTheme());
  const themeBtn = document.getElementById("themeToggle");
  if (themeBtn) themeBtn.addEventListener("click", toggleTheme);

  // Form behavior
  const btn = document.getElementById("createBtn");
  if (btn) btn.addEventListener("click", createPlaylist);

  const sourceEl = document.getElementById("source");
  if (sourceEl) sourceEl.addEventListener("change", updateTimeRangeState);

  const allBtn = document.getElementById("allSongsBtn");
  if (allBtn) {
    allBtn.addEventListener("click", () => {
      const sourceEl = document.getElementById("source");
      const limitEl = document.getElementById("limit");
      if (!sourceEl || !limitEl) return;

      if (sourceEl.value === "liked") {
        limitEl.value = "10000";
      }
    });
  }

  updateTimeRangeState();
});
