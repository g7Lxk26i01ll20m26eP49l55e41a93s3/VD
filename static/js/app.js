
// ==========================================================================
// 1. GLOBAL STATE & CONNECTION
// ==========================================================================
const socket = (typeof io !== "undefined") ? io({
  transports: ["websocket", "polling"],
  reconnection: true,
  reconnectionAttempts: Infinity,
  reconnectionDelay: 1000
}) : {
  on: function() {},
  emit: function() {},
  once: function() {},
  connected: false,
  _callbacks: {}
};
window.socket = socket;

let currentRoom = "";
window.currentRoom = "";
let currentRoomData = null;
window.currentRoomData = null;
let isCurrentRoomLeader = false;

let currentVideo = {
  type: "none",
  url: "",
  id: "",
  title: "",
  duration: 0,
  playing: false,
  time: 0,
  updated_at: 0
};
window.currentVideo = currentVideo;
let currentType = "none";
window.currentType = "none";

let currentUser = {
  id: "u_" + Math.random().toString(36).substring(2, 10),
  username: "Гость_" + Math.floor(100 + Math.random() * 900),
  display_name: "Гость",
  avatar: "",
  isGuest: true
};

let hlsPlayer = null;
let ytPlayer = null;
let ytApiReady = false;
let ytWatchdogInterval = null;
let syncCheckInterval = null;

let currentVolume = parseFloat(localStorage.getItem("vd_volume") || "1.0");
let isMuted = localStorage.getItem("vd_muted") === "true";
let isApplyingRemoteEvent = false;
let ignoreLocalEventsUntil = 0;
let isBuffering = false;
let currentPlaybackRate = 1.0;
let showRemainingTime = false;
let isScrubbingTimeline = false;
let controlsHideTimer = null;

// Server time offset synchronization
let serverTimeOffset = 0;

function handleServerTimeSample(serverTs) {
  if (serverTs && typeof serverTs === "number") {
    serverTimeOffset = (serverTs * 1000) - Date.now();
  }
}

function serverNow() {
  return (Date.now() + serverTimeOffset) / 1000;
}

function computeTargetTime() {
  if (!currentVideo) return 0;
  if (!currentVideo.playing) return currentVideo.time || 0;
  const elapsed = Math.max(0, serverNow() - (currentVideo.updated_at || serverNow()));
  return (currentVideo.time || 0) + elapsed;
}

// ==========================================================================
// 2. INITIALIZATION ON DOM READY
// ==========================================================================
document.addEventListener("DOMContentLoaded", function() {
  loadAuthSession();
  initChatCollapsing();
  initCustomPlayerControls();
  initDragAndDrop();
  initYouTubeApi();
  startSyncEngineLoop();
  startContinuousPingLoop();
  initFriendsSystem();

  // Check URL parameters (?room=...&code=...)
  const urlParams = new URLSearchParams(window.location.search);
  const targetRoom = urlParams.get("room");
  const roomCode = urlParams.get("code") || "";
  if (roomCode) currentRoomCode = roomCode;

  if (targetRoom) {
    joinRoomDirectly(targetRoom, roomCode);
  } else {
    showLobbyView();
    socket.emit("get_public_rooms");
    socket.emit("rooms_list");
  }

  // Keyboard Shortcuts (Space, K, F, C, M, J, L, Arrows)
  window.addEventListener("keydown", function(e) {
    if (e.target.tagName === "INPUT" || e.target.tagName === "TEXTAREA" || e.target.isContentEditable) return;
    const key = e.key;

    if (key === " " || key === "k" || key === "K" || key === "л" || key === "Л") {
      e.preventDefault();
      togglePlayPauseFromUI();
    } else if (key === "f" || key === "F" || key === "а" || key === "А") {
      e.preventDefault();
      toggleStageFullscreen();
    } else if (key === "c" || key === "C" || key === "с" || key === "С") {
      e.preventDefault();
      toggleChatSidebar();
    } else if (key === "m" || key === "M" || key === "ь" || key === "Ь") {
      e.preventDefault();
      toggleMuteFromUI();
    } else if (key === "ArrowLeft") {
      e.preventDefault();
      seekRelative(-5);
    } else if (key === "ArrowRight") {
      e.preventDefault();
      seekRelative(5);
    } else if (key === "j" || key === "J" || key === "о" || key === "О") {
      e.preventDefault();
      seekRelative(-10);
    } else if (key === "l" || key === "L" || key === "д" || key === "Д") {
      e.preventDefault();
      seekRelative(10);
    } else if (key === "ArrowUp") {
      e.preventDefault();
      changeVolumeFromUI(Math.min(1, currentVolume + 0.05));
    } else if (key === "ArrowDown") {
      e.preventDefault();
      changeVolumeFromUI(Math.max(0, currentVolume - 0.05));
    }
  });

  // Track Fullscreen state changes
  document.addEventListener("fullscreenchange", updateFullscreenUI);
  document.addEventListener("webkitfullscreenchange", updateFullscreenUI);
});

// ==========================================================================
// 3. COLLAPSIBLE CHAT SIDEBAR (THEATER FULL WIDTH)
// ==========================================================================
function initChatCollapsing() {
  const isCollapsed = localStorage.getItem("vd_chat_collapsed") === "true";
  if (isCollapsed) {
    setChatSidebarCollapsed(true);
  }
}

function toggleChatSidebar() {
  const roomView = document.getElementById("view-room");
  if (!roomView) return;
  const isCurrentlyCollapsed = roomView.classList.contains("chat-collapsed");
  setChatSidebarCollapsed(!isCurrentlyCollapsed);
}

function setChatSidebarCollapsed(collapsed) {
  const roomView = document.getElementById("view-room");
  const floatBtnText = document.getElementById("btn-floating-chat-text");
  const headerBtnLabel = document.getElementById("btn-toggle-chat-label");
  const floatPill = document.getElementById("btn-floating-chat-pill");
  if (!roomView) return;

  if (collapsed) {
    roomView.classList.add("chat-collapsed");
    if (floatBtnText) floatBtnText.textContent = "Показать чат";
    if (headerBtnLabel) headerBtnLabel.textContent = "Чат (скрыт)";
    if (floatPill) floatPill.style.display = "inline-flex";
    localStorage.setItem("vd_chat_collapsed", "true");
  } else {
    roomView.classList.remove("chat-collapsed");
    if (floatBtnText) floatBtnText.textContent = "Скрыть чат";
    if (headerBtnLabel) headerBtnLabel.textContent = "Чат";
    if (floatPill) floatPill.style.display = "none";
    localStorage.setItem("vd_chat_collapsed", "false");
    const box = document.getElementById("chat-messages");
    if (box) box.scrollTop = box.scrollHeight;
  }
}

function switchSidebarTab(tabName) {
  const btnChat = document.getElementById("tab-btn-chat");
  const btnMembers = document.getElementById("tab-btn-members");
  const paneChat = document.getElementById("pane-sidebar-chat");
  const paneMembers = document.getElementById("pane-sidebar-members");

  if (tabName === "chat") {
    if (btnChat) btnChat.classList.add("active");
    if (btnMembers) btnMembers.classList.remove("active");
    if (paneChat) paneChat.classList.add("active");
    if (paneMembers) paneMembers.classList.remove("active");
    const box = document.getElementById("chat-messages");
    if (box) box.scrollTop = box.scrollHeight;
  } else {
    if (btnChat) btnChat.classList.remove("active");
    if (btnMembers) btnMembers.classList.add("active");
    if (paneChat) paneChat.classList.remove("active");
    if (paneMembers) paneMembers.classList.add("active");
  }
}

// ==========================================================================
// 4. VIEW ROUTING (LOBBY vs ROOM)
// ==========================================================================
function showLobbyView() {
  document.getElementById("view-lobby").classList.add("active");
  document.getElementById("view-room").classList.remove("active");
  
  // Hide all room-specific elements from the top header on Lobby
  const roomElementsToHide = [
    "header-room-pill",
    "header-center-search",
    "header-catchup-pill",
    "btn-copy-room-link",
    "btn-toggle-chat",
    "btn-toggle-queue",
  ];
  roomElementsToHide.forEach(id => {
    const el = document.getElementById(id);
    if (el) el.style.display = "none";
  });

  stopAndTearDownAllPlayers();
  window.history.replaceState({}, "", "/");
  if (typeof fetchFriendsActivity === "function") {
    fetchFriendsActivity();
  }
}

function showRoomView() {
  document.getElementById("view-lobby").classList.remove("active");
  document.getElementById("view-room").classList.add("active");

  const searchEl = document.getElementById("header-center-search");
  if (searchEl) searchEl.style.display = "flex";

  const roomElementsToShow = [
    "header-room-pill",
    "btn-copy-room-link",
    "btn-toggle-chat",
    "btn-toggle-queue",
  ];
  roomElementsToShow.forEach(id => {
    const el = document.getElementById(id);
    if (el) el.style.display = "inline-flex";
  });
}

function goToLobby() {
  if (currentRoom) {
    leaveCurrentRoom();
  } else {
    showLobbyView();
  }
}

// ==========================================================================
// 5. ROOM MANAGEMENT (PRIVATE 1-ON-1 PROTECTION BY DEFAULT)
// ==========================================================================
let currentRoomCode = "";

function createRoomDirectly(isPrivate = true) {
  showToast(isPrivate ? "🔒 Создание приватной комнаты для двоих..." : "Создание комнаты совместного просмотра...");
  socket.emit("create_room", {
    name: "Кинозал " + currentUser.username,
    private: isPrivate,
    user: {
      id: currentUser.id,
      name: currentUser.username,
      avatar: currentUser.avatar
    }
  });
}

function joinRoomDirectly(roomId, code) {
  if (currentRoom !== roomId) {
    stopAndTearDownAllPlayers();
  }
  currentRoom = roomId;
  if (code) currentRoomCode = code;
  socket.emit("join_room", {
    room_id: roomId,
    code: currentRoomCode || "",
    account_id: currentUser.id,
    user: {
      id: currentUser.id,
      name: currentUser.username,
      username: currentUser.username,
      avatar: currentUser.avatar
    }
  });
  showRoomView();
  updateRoomHeaderInfo(roomId);
}

function leaveCurrentRoom() {
  if (currentRoom) {
    socket.emit("leave_room", { room_id: currentRoom });
  }
  currentRoom = "";
  currentRoomData = null;
  isCurrentRoomLeader = false;
  showLobbyView();
  socket.emit("get_public_rooms");
}

function updateRoomHeaderInfo(roomId) {
  window.currentRoom = roomId;
  currentRoom = roomId;
  const nameEl = document.getElementById("header-room-name");
  const isPrivate = (currentRoomData && currentRoomData.private) || !!currentRoomCode;
  if (nameEl) {
    nameEl.innerHTML = isPrivate ? `🔒 ${currentRoomData ? currentRoomData.name : 'Приватная комната'}` : (currentRoomData ? currentRoomData.name : `Комната ${roomId}`);
  }
  const codeParam = currentRoomCode ? `&code=${encodeURIComponent(currentRoomCode)}` : "";
  window.history.replaceState({}, "", `/?room=${encodeURIComponent(roomId)}${codeParam}`);
}

function copyInviteLink() {
  const codeParam = currentRoomCode ? `&code=${encodeURIComponent(currentRoomCode)}` : "";
  const url = `${window.location.origin}/?room=${encodeURIComponent(currentRoom)}${codeParam}`;
  navigator.clipboard.writeText(url).then(() => {
    showToast(currentRoomCode ? "🔒 Секретная ссылка скопирована! Отправьте её Вике." : "📋 Ссылка скопирована!");
  }).catch(() => {
    showToast("Ссылка: " + url);
  });
}

// ==========================================================================
// ==========================================================================
// SCREEN WAKELOCK API (Keeps screen awake on mobile and desktop during playback)
// ==========================================================================
let wakeLockSentinel = null;

async function requestWakeLock() {
  if (!("wakeLock" in navigator)) return;
  if (wakeLockSentinel && !wakeLockSentinel.released) return;
  try {
    wakeLockSentinel = await navigator.wakeLock.request("screen");
    wakeLockSentinel.addEventListener("release", () => {
      wakeLockSentinel = null;
    });
    console.log("[VD] Screen WakeLock acquired");
  } catch (e) {
    wakeLockSentinel = null;
  }
}

async function releaseWakeLock() {
  if (wakeLockSentinel) {
    try {
      await wakeLockSentinel.release();
    } catch (e) {}
    wakeLockSentinel = null;
    console.log("[VD] Screen WakeLock released");
  }
}

document.addEventListener("visibilitychange", async () => {
  if (document.visibilityState === "visible") {
    const isPlaying = (currentVideo && currentVideo.playing) ||
      (currentType === "youtube" && ytPlayer && typeof ytPlayer.getPlayerState === "function" && ytPlayer.getPlayerState() === 1) ||
      (currentType !== "youtube" && (() => { const v = document.getElementById("rave-video-el"); return v && !v.paused && !v.ended; })());
    if (isPlaying) {
      await requestWakeLock();
    }
  }
});

// 6. ROCK-SOLID PLAYER ENGINE & CUSTOM CONTROLS OVERLAY
// ==========================================================================
function initCustomPlayerControls() {
  const videoEl = document.getElementById("rave-video-el");
  const stage = document.getElementById("player-stage-wrap");
  const timelineContainer = document.getElementById("player-timeline-container");
  const hoverTooltip = document.getElementById("timeline-hover-tooltip");

  // Mouse move over player to show controls & auto-hide timer
  if (stage) {
    stage.addEventListener("mousemove", handlePlayerStageMouseMove);
    stage.addEventListener("touchstart", handlePlayerStageMouseMove, { passive: true });
    stage.addEventListener("mouseleave", () => {
      const v = document.getElementById("rave-video-el");
      if (v && !v.paused && !isScrubbingTimeline) {
        stage.classList.add("controls-hidden");
      }
    });
  }

  // Native Video element events
  if (videoEl) {
    videoEl.addEventListener("click", function(e) {
      e.stopPropagation();
      togglePlayPauseFromUI();
    });
    videoEl.addEventListener("timeupdate", onVideoTimeUpdate);
    videoEl.addEventListener("progress", onVideoBufferProgress);
    videoEl.addEventListener("loadedmetadata", onVideoLoadedMetadata);
    videoEl.addEventListener("play", () => {
      requestWakeLock();
      updatePlayPauseUI(true);
      flashPlayPauseIcon(true);
    });
    videoEl.addEventListener("pause", () => {
      releaseWakeLock();
      updatePlayPauseUI(false);
      flashPlayPauseIcon(false);
      if (stage) stage.classList.remove("controls-hidden");
    });
    videoEl.addEventListener("ended", () => {
      releaseWakeLock();
      onVideoEnded();
    });
    videoEl.addEventListener("error", function() {
      const err = videoEl.error;
      console.error("[Player] Video error:", err);
      if (err && err.code === 4) {
        showToast("⚠️ Ошибка формата: загрузите файл _faststart.mp4 из Загрузок на Pixeldrain");
      }
    });
    videoEl.addEventListener("volumechange", updateVolumeUI);
  }

  // Timeline scrubber hover & scrubbing
  if (timelineContainer) {
    timelineContainer.addEventListener("mousemove", function(e) {
      const v = document.getElementById("rave-video-el");
      const duration = (v && v.duration) ? v.duration : (currentVideo.duration || 0);
      if (!duration || !hoverTooltip) return;
      const rect = timelineContainer.getBoundingClientRect();
      const frac = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));
      hoverTooltip.style.left = `${frac * 100}%`;
      hoverTooltip.textContent = formatMediaTime(frac * duration);
    });

    timelineContainer.addEventListener("mousedown", function(e) {
      isScrubbingTimeline = true;
      timelineContainer.classList.add("scrubbing");
      handleTimelineScrub(e);

      function onMove(me) {
        if (isScrubbingTimeline) handleTimelineScrub(me);
      }
      function onUp() {
        isScrubbingTimeline = false;
        timelineContainer.classList.remove("scrubbing");
        window.removeEventListener("mousemove", onMove);
        window.removeEventListener("mouseup", onUp);
      }
      window.addEventListener("mousemove", onMove);
      window.addEventListener("mouseup", onUp);
    });

    timelineContainer.addEventListener("touchstart", function(e) {
      isScrubbingTimeline = true;
      timelineContainer.classList.add("scrubbing");
      handleTimelineScrub(e);

      function onTouchMove(te) {
        if (isScrubbingTimeline) handleTimelineScrub(te);
      }
      function onTouchEnd() {
        isScrubbingTimeline = false;
        timelineContainer.classList.remove("scrubbing");
        window.removeEventListener("touchmove", onTouchMove);
        window.removeEventListener("touchend", onTouchEnd);
      }
      window.addEventListener("touchmove", onTouchMove, { passive: true });
      window.addEventListener("touchend", onTouchEnd);
    }, { passive: true });
  }

  // Gesture Layer (Double clicks & touches for -10s / +10s / Fullscreen, single click/touch for Controls)
  const zoneLeft = document.getElementById("zone-seek-left");
  const zoneRight = document.getElementById("zone-seek-right");
  const zoneCenter = document.getElementById("zone-center-play");

  if (zoneLeft) {
    zoneLeft.addEventListener("dblclick", function(e) {
      e.stopPropagation();
      seekRelative(-10);
    });
    let lastLeftTouch = 0;
    zoneLeft.addEventListener("touchend", function(e) {
      const now = Date.now();
      if (now - lastLeftTouch < 340) {
        e.preventDefault();
        e.stopPropagation();
        seekRelative(-10);
        lastLeftTouch = 0;
      } else {
        lastLeftTouch = now;
      }
    }, { passive: false });
  }

  if (zoneRight) {
    zoneRight.addEventListener("dblclick", function(e) {
      e.stopPropagation();
      seekRelative(10);
    });
    let lastRightTouch = 0;
    zoneRight.addEventListener("touchend", function(e) {
      const now = Date.now();
      if (now - lastRightTouch < 340) {
        e.preventDefault();
        e.stopPropagation();
        seekRelative(10);
        lastRightTouch = 0;
      } else {
        lastRightTouch = now;
      }
    }, { passive: false });
  }

  if (zoneCenter) {
    let clickTimeout = null;
    zoneCenter.addEventListener("click", function(e) {
      if (clickTimeout) {
        clearTimeout(clickTimeout);
        clickTimeout = null;
        toggleStageFullscreen();
      } else {
        clickTimeout = setTimeout(() => {
          clickTimeout = null;
          togglePlayPauseFromUI();
        }, 220);
      }
    });

    let lastCenterTouch = 0;
    let centerTouchTimer = null;
    zoneCenter.addEventListener("touchend", function(e) {
      const now = Date.now();
      if (now - lastCenterTouch < 340) {
        e.preventDefault();
        e.stopPropagation();
        if (centerTouchTimer) clearTimeout(centerTouchTimer);
        centerTouchTimer = null;
        lastCenterTouch = 0;
        toggleStageFullscreen();
      } else {
        lastCenterTouch = now;
        centerTouchTimer = setTimeout(() => {
          centerTouchTimer = null;
          const stage = document.getElementById("player-stage-wrap");
          if (stage) {
            if (stage.classList.contains("controls-hidden")) {
              handlePlayerStageMouseMove();
            } else {
              stage.classList.add("controls-hidden");
            }
          }
        }, 260);
      }
    }, { passive: false });
  }

  // Initialize Volume from storage
  applyVolumeToPlayers();
  updateVolumeUI();
}

function handlePlayerStageMouseMove() {
  const stage = document.getElementById("player-stage-wrap");
  if (!stage) return;
  stage.classList.remove("controls-hidden");
  if (controlsHideTimer) clearTimeout(controlsHideTimer);
  const videoEl = document.getElementById("rave-video-el");
  if (videoEl && !videoEl.paused && currentType !== "none") {
    controlsHideTimer = setTimeout(() => {
      const v = document.getElementById("rave-video-el");
      if (v && !v.paused && !isScrubbingTimeline) {
        stage.classList.add("controls-hidden");
      }
    }, 2500);
  }
}

function onVideoTimeUpdate() {
  const videoEl = document.getElementById("rave-video-el");
  if (!videoEl) return;
  const cur = videoEl.currentTime || 0;
  const dur = videoEl.duration || (currentVideo.duration || 0);

  // Update Scrubber
  const progressBar = document.getElementById("timeline-progress-bar");
  if (progressBar && dur > 0) {
    const pct = Math.min(100, Math.max(0, (cur / dur) * 100));
    progressBar.style.width = `${pct}%`;
  }

  // Update Time display
  const curTimeEl = document.getElementById("player-current-time");
  const durTimeEl = document.getElementById("player-duration-time");
  if (curTimeEl) curTimeEl.textContent = formatMediaTime(cur);
  if (durTimeEl) {
    if (showRemainingTime && dur > 0) {
      durTimeEl.textContent = "-" + formatMediaTime(Math.max(0, dur - cur));
    } else {
      durTimeEl.textContent = formatMediaTime(dur);
    }
  }
}

function onVideoBufferProgress() {
  const videoEl = document.getElementById("rave-video-el");
  const bufferBar = document.getElementById("timeline-buffer-bar");
  if (!videoEl || !bufferBar || !videoEl.duration) return;
  const dur = videoEl.duration;
  if (videoEl.buffered && videoEl.buffered.length > 0) {
    const end = videoEl.buffered.end(videoEl.buffered.length - 1);
    const pct = Math.min(100, Math.max(0, (end / dur) * 100));
    bufferBar.style.width = `${pct}%`;
  }
}

function onVideoLoadedMetadata() {
  const videoEl = document.getElementById("rave-video-el");
  if (!videoEl) return;
  const durTimeEl = document.getElementById("player-duration-time");
  if (durTimeEl) durTimeEl.textContent = formatMediaTime(videoEl.duration);
}

function handleTimelineScrub(e) {
  const container = document.getElementById("player-timeline-container");
  const videoEl = document.getElementById("rave-video-el");
  if (!container) return;
  const rect = container.getBoundingClientRect();
  const clientX = e.clientX !== undefined ? e.clientX : (e.touches && e.touches[0] ? e.touches[0].clientX : 0);
  const frac = Math.max(0, Math.min(1, (clientX - rect.left) / rect.width));

  if (currentType === "youtube" && ytPlayer) {
    const dur = ytPlayer.getDuration ? ytPlayer.getDuration() : 0;
    if (dur > 0) {
      const targetTime = frac * dur;
      playerSeekTo(targetTime);
      if (currentRoom) socket.emit("video_seek", { room_id: currentRoom, time: targetTime, source_sid: socket.id });
    }
  } else if (videoEl && videoEl.duration) {
    const targetTime = frac * videoEl.duration;
    playerSeekTo(targetTime);
    onVideoTimeUpdate();
    if (currentRoom) socket.emit("video_seek", { room_id: currentRoom, time: targetTime, source_sid: socket.id });
  }
}

function togglePlayPauseFromUI() {
  if (currentType === "youtube") {
    const p = ytPlayer || window.ytPlayer;
    const curTime = (p && typeof p.getCurrentTime === "function") ? p.getCurrentTime() : (currentVideo.time || 0);
    const pState = (p && typeof p.getPlayerState === "function") ? p.getPlayerState() : -1;
    const isCurrentlyPlaying = (pState === 1 || (pState !== 2 && currentVideo && currentVideo.playing));

    isApplyingRemoteEvent = true;
    if (isCurrentlyPlaying) {
      // Playing -> Pause
      currentVideo.playing = false;
      currentVideo.time = curTime;
      currentVideo.updated_at = serverNow();
      window.currentVideo = currentVideo;
      if (p && typeof p.pauseVideo === "function") {
        try { p.pauseVideo(); } catch(e) {}
      }
      if (currentRoom) {
        socket.emit("video_pause", { room_id: currentRoom, time: curTime, source_sid: socket.id });
      }
    } else {
      // Paused -> Play
      currentVideo.playing = true;
      currentVideo.time = curTime;
      currentVideo.updated_at = serverNow();
      window.currentVideo = currentVideo;
      if (p && typeof p.playVideo === "function") {
        try { p.playVideo(); } catch(e) {}
      }
      if (currentRoom) {
        socket.emit("video_play", { room_id: currentRoom, time: curTime, source_sid: socket.id });
      }
    }
    setTimeout(() => { isApplyingRemoteEvent = false; }, 500);
    return;
  }

  const el = document.getElementById("rave-video-el");
  if (!el) return;
  const isCurrentlyPlaying = !el.paused;
  if (isCurrentlyPlaying) {
    currentVideo.playing = false;
    currentVideo.time = el.currentTime;
    currentVideo.updated_at = serverNow();
    window.currentVideo = currentVideo;
    el.pause();
    updatePlayPauseUI(false);
    flashPlayPauseIcon(false);
    if (currentRoom) {
      socket.emit("video_pause", { room_id: currentRoom, time: el.currentTime, source_sid: socket.id });
    }
  } else {
    currentVideo.playing = true;
    currentVideo.time = el.currentTime;
    currentVideo.updated_at = serverNow();
    window.currentVideo = currentVideo;
    safePlayMedia(el);
    updatePlayPauseUI(true);
    flashPlayPauseIcon(true);
    if (currentRoom) {
      socket.emit("video_play", { room_id: currentRoom, time: el.currentTime, source_sid: socket.id });
    }
  }
}

function seekRelative(deltaSeconds) {
  const cur = currentPlayerTime();
  const target = Math.max(0, cur + deltaSeconds);
  playerSeekTo(target);
  if (currentRoom) {
    socket.emit("video_seek", { room_id: currentRoom, time: target, source_sid: socket.id });
  }

  // Trigger gesture badge ripple
  const badgeId = deltaSeconds < 0 ? "ripple-left" : "ripple-right";
  const badge = document.getElementById(badgeId);
  if (badge) {
    badge.classList.add("active");
    clearTimeout(badge._timer);
    badge._timer = setTimeout(() => badge.classList.remove("active"), 500);
  }
}

function toggleTimeRemainingDisplay() {
  showRemainingTime = !showRemainingTime;
  onVideoTimeUpdate();
}

function changeVolumeFromUI(val) {
  currentVolume = parseFloat(val);
  isMuted = (currentVolume <= 0.001);
  localStorage.setItem("vd_volume", currentVolume);
  localStorage.setItem("vd_muted", isMuted);
  applyVolumeToPlayers();
  updateVolumeUI();
}

function toggleMuteFromUI() {
  isMuted = !isMuted;
  localStorage.setItem("vd_muted", isMuted);
  applyVolumeToPlayers();
  updateVolumeUI();
}

function updateVolumeUI() {
  const btn = document.getElementById("btn-ctrl-volume");
  const slider = document.getElementById("player-volume-slider");
  if (slider) slider.value = isMuted ? 0 : currentVolume;
  if (btn) {
    const volHigh = btn.querySelector(".icon-vol-high");
    const volMute = btn.querySelector(".icon-vol-mute");
    if (volHigh) volHigh.style.display = isMuted ? "none" : "block";
    if (volMute) volMute.style.display = isMuted ? "block" : "none";
  }
}

function applyVolumeToPlayers() {
  const videoEl = document.getElementById("rave-video-el");
  if (videoEl) {
    videoEl.muted = isMuted;
    videoEl.volume = isMuted ? 0 : currentVolume;
  }
  if (ytPlayer && typeof ytPlayer.setVolume === "function") {
    try {
      if (isMuted) ytPlayer.mute();
      else {
        ytPlayer.unMute();
        ytPlayer.setVolume(currentVolume * 100);
      }
    } catch(e) {}
  }
}

function updatePlayPauseUI(isPlaying) {
  const btn = document.getElementById("btn-ctrl-play");
  if (!btn) return;
  const playIcon = btn.querySelector(".icon-play");
  const pauseIcon = btn.querySelector(".icon-pause");
  if (playIcon) playIcon.style.display = isPlaying ? "none" : "block";
  if (pauseIcon) pauseIcon.style.display = isPlaying ? "block" : "none";
}

function updatePlayPauseIcons(isPlaying) {
  updatePlayPauseUI(isPlaying);
}

function flashPlayPauseIcon(isPlaying) {
  const flash = document.getElementById("center-play-flash");
  if (!flash) return;
  const playSvg = flash.querySelector(".flash-icon-play");
  const pauseSvg = flash.querySelector(".flash-icon-pause");
  if (playSvg) playSvg.style.display = isPlaying ? "block" : "none";
  if (pauseSvg) pauseSvg.style.display = isPlaying ? "none" : "block";
  flash.classList.add("flash");
  clearTimeout(flash._timer);
  flash._timer = setTimeout(() => {
    flash.classList.remove("flash");
  }, 400);
}

function closeAllDropdowns() {
  const sMenu = document.getElementById("speed-dropdown-menu");
  const aMenu = document.getElementById("audio-dropdown-menu");
  const qMenu = document.getElementById("quality-dropdown-menu");
  if (sMenu) { sMenu.classList.remove("active"); sMenu.style.display = "none"; }
  if (aMenu) { aMenu.classList.remove("active"); aMenu.style.display = "none"; }
  if (qMenu) { qMenu.classList.remove("active"); qMenu.style.display = "none"; }
}

function toggleSpeedMenu() {
  const menu = document.getElementById("speed-dropdown-menu");
  if (!menu) return;
  const isAct = menu.classList.contains("active");
  closeAllDropdowns();
  if (!isAct) {
    menu.classList.add("active");
    menu.style.display = "flex";
  }
}

function toggleAudioMenu() {
  const menu = document.getElementById("audio-dropdown-menu");
  if (!menu) return;
  const isAct = menu.classList.contains("active");
  closeAllDropdowns();
  if (!isAct) {
    menu.classList.add("active");
    menu.style.display = "flex";
  }
}

function toggleQualityMenu() {
  const menu = document.getElementById("quality-dropdown-menu");
  if (!menu) return;
  const isAct = menu.classList.contains("active");
  closeAllDropdowns();
  if (!isAct) {
    menu.classList.add("active");
    menu.style.display = "flex";
  }
}

function updateQualityLevelsUI() {
  const wrap = document.getElementById("player-quality-menu-wrap");
  const menu = document.getElementById("quality-dropdown-menu");
  if (!wrap || !menu) return;

  const player = hlsPlayer || window.hlsPlayer;
  if (!player || !player.levels || player.levels.length <= 1) {
    wrap.style.display = "none";
    menu.classList.remove("active");
    menu.style.display = "none";
    return;
  }

  wrap.style.display = "inline-flex";
  menu.innerHTML = "";

  // 1. Auto Option
  const autoOpt = document.createElement("div");
  const isAuto = player.currentLevel === -1;
  autoOpt.className = "quality-opt" + (isAuto ? " active" : "");
  autoOpt.innerHTML = `<span>Auto (Адаптивное)</span>${isAuto ? '<span style="color:var(--primary); font-weight:700;">✓</span>' : ''}`;
  autoOpt.onclick = (e) => { e.stopPropagation(); selectQualityLevel(-1); };
  menu.appendChild(autoOpt);

  // 2. Sorted Levels (Highest to Lowest)
  const levelsWithIdx = player.levels.map((lvl, idx) => ({ ...lvl, idx }));
  levelsWithIdx.sort((a, b) => (b.height || 0) - (a.height || 0));

  levelsWithIdx.forEach(lvl => {
    const opt = document.createElement("div");
    const isCur = player.currentLevel === lvl.idx;
    opt.className = "quality-opt" + (isCur ? " active" : "");
    let label = lvl.height ? `${lvl.height}p` : (lvl.bitrate ? `${Math.round(lvl.bitrate / 1000)} kbps` : `Уровень ${lvl.idx + 1}`);
    if (lvl.height >= 1080) label += " (FHD)";
    else if (lvl.height >= 720) label += " (HD)";

    opt.innerHTML = `<span>${label}</span>${isCur ? '<span style="color:var(--primary); font-weight:700;">✓</span>' : ''}`;
    opt.onclick = (e) => { e.stopPropagation(); selectQualityLevel(lvl.idx); };
    menu.appendChild(opt);
  });

  updateQualityButtonLabel();
}

function selectQualityLevel(levelIdx) {
  const player = hlsPlayer || window.hlsPlayer;
  if (!player) return;
  player.currentLevel = levelIdx;
  try {
    localStorage.setItem("vd_preferred_quality", String(levelIdx));
  } catch(e) {}

  updateQualityLevelsUI();
  closeAllDropdowns();

  let name = "Auto";
  if (levelIdx >= 0 && player.levels && player.levels[levelIdx]) {
    const lvl = player.levels[levelIdx];
    name = lvl.height ? `${lvl.height}p` : `${levelIdx}`;
  }
  showToast(`🎬 Качество: ${name}`);
}

function updateQualityButtonLabel() {
  const btnLabel = document.getElementById("quality-btn-label");
  if (!btnLabel) return;
  const player = hlsPlayer || window.hlsPlayer;
  if (!player) {
    btnLabel.textContent = "Auto";
    return;
  }
  if (player.currentLevel === -1) {
    const activeLevel = player.levels && player.levels[player.currentLevel >= 0 ? player.currentLevel : player.loadLevel];
    if (activeLevel && activeLevel.height) {
      btnLabel.textContent = `Auto (${activeLevel.height}p)`;
    } else {
      btnLabel.textContent = "Auto";
    }
  } else if (player.levels && player.levels[player.currentLevel]) {
    const lvl = player.levels[player.currentLevel];
    btnLabel.textContent = lvl.height ? `${lvl.height}p` : "HD";
  }
}

function updateAudioTracksUI() {
  const wrap = document.getElementById("player-audio-menu-wrap");
  const menu = document.getElementById("audio-dropdown-menu");
  if (!wrap || !menu) return;

  let tracks = [];
  // 1. Try Hls.js native audio tracks
  if (hlsPlayer && hlsPlayer.audioTracks && hlsPlayer.audioTracks.length > 1) {
    tracks = hlsPlayer.audioTracks.map((t, idx) => {
      let flag = "🎙️";
      let name = t.name || `Дорожка ${idx + 1}`;
      const metaTracks = (currentVideo && currentVideo.audio_tracks) ? currentVideo.audio_tracks : [];
      if (metaTracks[idx]) {
        name = metaTracks[idx].name || name;
        flag = metaTracks[idx].flag || flag;
      } else {
        const lang = (t.lang || "").toLowerCase();
        if (lang === "uk" || lang === "ua") flag = "🇺🇦";
        else if (lang === "ru") flag = "🇷🇺";
        else if (lang === "en") flag = "🇬🇧";
      }

      return { id: idx, name: name, flag: flag, active: idx === hlsPlayer.audioTrack };
    });
  } else if (currentVideo && currentVideo.audio_tracks && currentVideo.audio_tracks.length > 1) {
    tracks = currentVideo.audio_tracks.map((t, idx) => ({
      id: idx,
      name: t.name || `Дорожка ${idx + 1}`,
      flag: t.flag || "🎙️",
      active: idx === (currentVideo.selected_audio || 0)
    }));
  }

  if (!tracks.length || tracks.length <= 1) {
    wrap.style.display = "none";
    menu.classList.remove("active");
    menu.style.display = "none";
    return;
  }

  wrap.style.display = "inline-flex";
  menu.innerHTML = "";
  tracks.forEach(tr => {
    const opt = document.createElement("div");
    opt.className = "audio-opt" + (tr.active ? " active" : "");
    opt.innerHTML = `
      <span class="audio-opt-flag">${tr.flag}</span>
      <span class="audio-opt-name" style="flex:1;">${escapeHTML(tr.name)}</span>
      ${tr.active ? '<span class="audio-opt-check" style="color:var(--primary); font-weight:700;">✓</span>' : ''}
    `;
    opt.onclick = (e) => { e.stopPropagation(); selectAudioTrack(tr.id, tr.name); };
    menu.appendChild(opt);
  });
}

function selectAudioTrack(trackIndex, trackName) {
  if (hlsPlayer && typeof hlsPlayer.audioTrack !== "undefined") {
    try {
      hlsPlayer.audioTrack = trackIndex;
    } catch(e) {}
  }
  if (currentVideo) {
    currentVideo.selected_audio = trackIndex;
  }
  closeAllDropdowns();
  updateAudioTracksUI();
  showToast(`🎙️ Озвучка: ${trackName || 'Выбрана'}`);
}

function sendEmojiReaction(emoji) {
  if (!currentRoom) {
    showToast("Реакции доступны внутри комнаты просмотра");
    return;
  }
  const user = currentUser ? (currentUser.username || currentUser.name || "Гость") : "Гость";
  socket.emit("send_reaction", {
    room_id: currentRoom,
    emoji: emoji,
    user: user
  });
  spawnFloatingEmoji(emoji);
}

function spawnFloatingEmoji(emoji) {
  const layer = document.getElementById("reaction-layer");
  if (!layer || !emoji) return;

  const el = document.createElement("div");
  el.className = "floating-emoji";
  el.textContent = emoji;

  // Natural randomized spread on right portion of video (62% to 92%)
  const leftPct = 62 + Math.random() * 28;
  el.style.left = leftPct.toFixed(1) + "%";

  const rotStart = (Math.random() * 22 - 11).toFixed(1);
  const rotMid = (Math.random() * 22 - 11).toFixed(1);
  const rotEnd = (Math.random() * 28 - 14).toFixed(1);
  el.style.setProperty("--rot-deg", rotStart + "deg");
  el.style.setProperty("--rot-deg-mid", rotMid + "deg");
  el.style.setProperty("--rot-deg-end", rotEnd + "deg");

  el.addEventListener("animationend", () => {
    try { el.remove(); } catch(e) {}
  });
  setTimeout(() => { try { el.remove(); } catch(e) {} }, 3000);
  layer.appendChild(el);
}

function setSpeedFromUI(rate) {
  setPlayerPlaybackRate(rate);
  const label = document.getElementById("speed-btn-label");
  if (label) label.textContent = rate + "x";
  const menu = document.getElementById("speed-dropdown-menu");
  if (menu) {
    menu.classList.remove("active");
    menu.querySelectorAll(".speed-opt").forEach(opt => {
      opt.classList.toggle("active", opt.textContent.startsWith(rate + "x"));
    });
  }
}

function togglePictureInPicture() {
  const videoEl = document.getElementById("rave-video-el");
  if (!videoEl) return;
  if (document.pictureInPictureElement) {
    document.exitPictureInPicture().catch(() => {});
  } else if (videoEl.requestPictureInPicture) {
    videoEl.requestPictureInPicture().catch(() => {});
  }
}

function toggleStageFullscreen() {
  const stage = document.getElementById("player-stage-wrap") || document.documentElement;
  const isFs = !!(document.fullscreenElement || document.webkitFullscreenElement);
  if (!isFs) {
    if (stage.requestFullscreen) stage.requestFullscreen();
    else if (stage.webkitRequestFullscreen) stage.webkitRequestFullscreen();
  } else {
    if (document.exitFullscreen) document.exitFullscreen();
    else if (document.webkitExitFullscreen) document.webkitExitFullscreen();
  }
}

function updateFullscreenUI() {
  const btn = document.getElementById("btn-ctrl-fullscreen");
  if (!btn) return;
  const isFs = !!(document.fullscreenElement || document.webkitFullscreenElement);
  const iconEnter = btn.querySelector(".icon-fs-enter");
  const iconExit = btn.querySelector(".icon-fs-exit");
  if (iconEnter) iconEnter.style.display = isFs ? "none" : "block";
  if (iconExit) iconExit.style.display = isFs ? "block" : "none";
}

function formatMediaTime(sec) {
  if (!sec || isNaN(sec) || sec < 0) sec = 0;
  sec = Math.floor(sec);
  const h = Math.floor(sec / 3600);
  const m = Math.floor((sec % 3600) / 60);
  const s = sec % 60;
  if (h > 0) {
    return `${h}:${m < 10 ? '0' : ''}${m}:${s < 10 ? '0' : ''}${s}`;
  }
  return `${m < 10 ? '0' : ''}${m}:${s < 10 ? '0' : ''}${s}`;
}

// ==========================================================================
// 7. VIDEO LIFECYCLE & MOUNTING (YOUTUBE & HTML5)
// ==========================================================================
function resetYouTubeDOMTarget() {
  if (ytWatchdogInterval) {
    clearInterval(ytWatchdogInterval);
    ytWatchdogInterval = null;
  }
  if (ytPlayer) {
    try {
      if (typeof ytPlayer.stopVideo === "function") ytPlayer.stopVideo();
      if (typeof ytPlayer.destroy === "function") ytPlayer.destroy();
    } catch(e) {}
    ytPlayer = null;
    window.ytPlayer = null;
  }
  const slot = document.getElementById("yt-player-slot");
  if (slot) {
    slot.innerHTML = '<div id="yt-player-target"></div>';
    slot.style.display = "none";
  }
}

function stopAndTearDownAllPlayers() {
  resetYouTubeDOMTarget();
  if (hlsPlayer) {
    try {
      hlsPlayer.stopLoad();
      hlsPlayer.destroy();
    } catch(e) {}
    hlsPlayer = null;
  }
  const videoEl = document.getElementById("rave-video-el");
  if (videoEl) {
    try {
      videoEl.pause();
      videoEl.removeAttribute("src");
      videoEl.load();
      videoEl.style.display = "none";
    } catch(e) {}
  }
  const embedSlot = document.getElementById("embed-player-slot");
  const embedIframe = document.getElementById("embed-player-iframe");
  if (embedSlot) embedSlot.style.display = "none";
  if (embedIframe) embedIframe.src = "about:blank";
  const audioWrap = document.getElementById("player-audio-menu-wrap");
  const audioMenu = document.getElementById("audio-dropdown-menu");
  if (audioWrap) audioWrap.style.display = "none";
  if (audioMenu) audioMenu.classList.remove("active");
  releaseWakeLock();

  currentVideo = { type: "none", url: "", id: "", title: "", duration: 0, playing: false, time: 0, updated_at: 0 };
  currentType = "none";
  isBuffering = false;

  const emptyPlaceholder = document.getElementById("empty-player-placeholder");
  if (emptyPlaceholder) emptyPlaceholder.style.display = "flex";
  const customOverlay = document.getElementById("vd-player-overlay");
  if (customOverlay) customOverlay.style.display = "none";
  const qWrap = document.getElementById("player-quality-menu-wrap");
  if (qWrap) qWrap.style.display = "none";
  const aWrap = document.getElementById("player-audio-menu-wrap");
  if (aWrap) aWrap.style.display = "none";
  const epWrap = document.getElementById("player-episodes-wrap");
  if (epWrap) epWrap.style.display = "none";
  hideCatchupButton();
}

function renderPlayer(video) {
  if (video && video.video) video = video.video;
  if (!video || !video.url) {
    stopAndTearDownAllPlayers();
    return;
  }

  // Update title in top bar
  const titleTextEl = document.getElementById("player-title-text");
  if (titleTextEl) {
    titleTextEl.textContent = video.title || "Видео";
  }

  // If already playing identical URL, smoothly update metadata and play state without seeking
  if (currentVideo && currentVideo.url === video.url) {
    currentVideo.title = video.title || currentVideo.title;
    // Don't let older remote state packets override newer local user interaction
    if (video.updated_at && currentVideo.updated_at && video.updated_at < currentVideo.updated_at) {
      return;
    }
    currentVideo.playing = !!video.playing;
    currentVideo.updated_at = video.updated_at || serverNow();
    window.currentVideo = currentVideo;
    isApplyingRemoteEvent = true;
    if (video.playing) {
      requestWakeLock();
      if (currentType === "youtube" && ytPlayer && ytPlayer.playVideo) {
        try { ytPlayer.playVideo(); } catch(e) {}
      } else if (currentType !== "youtube" && currentType !== "embed" && currentType !== "iframe") {
        const el = document.getElementById("rave-video-el");
        if (el && el.paused) safePlayMedia(el);
      }
    } else {
      releaseWakeLock();
      if (currentType === "youtube" && ytPlayer && ytPlayer.pauseVideo) {
        try { ytPlayer.pauseVideo(); } catch(e) {}
      } else if (currentType !== "youtube" && currentType !== "embed" && currentType !== "iframe") {
        const el = document.getElementById("rave-video-el");
        if (el && !el.paused) el.pause();
      }
    }
    updatePlayPauseIcons(currentVideo.playing);
    setTimeout(() => { isApplyingRemoteEvent = false; }, 400);
    return;
  }

  currentVideo = video;
  window.currentVideo = video;
  currentType = currentVideo.type || "none";
  window.currentType = currentType;

  // Toggle episodes drawer button if series
  const epBtnWrap = document.getElementById("player-episodes-wrap");
  if (epBtnWrap) {
    if (currentVideo.season && currentVideo.episode) {
      epBtnWrap.style.display = "inline-flex";
    } else {
      epBtnWrap.style.display = "none";
    }
  }

  const emptyPlaceholder = document.getElementById("empty-player-placeholder");
  if (emptyPlaceholder) emptyPlaceholder.style.display = "none";

  const videoEl = document.getElementById("rave-video-el");
  const slot = document.getElementById("yt-player-slot");
  const customOverlay = document.getElementById("vd-player-overlay");
  const embedSlot = document.getElementById("embed-player-slot");
  const embedIframe = document.getElementById("embed-player-iframe");

  if (currentType === "youtube") {
    // Hide HTML5 video and embed player, show YouTube
    if (embedSlot) { embedSlot.style.display = "none"; if (embedIframe) embedIframe.src = "about:blank"; }
    if (hlsPlayer) { try { hlsPlayer.destroy(); } catch(e) {} hlsPlayer = null; }
    if (videoEl) {
      try {
        videoEl.pause();
        videoEl.removeAttribute("src");
        videoEl.load();
        videoEl.style.display = "none";
      } catch(e) {}
    }
    if (slot) slot.style.display = "block";
    if (customOverlay) {
      customOverlay.style.display = "none";
    }
    mountYouTubeVideo(currentVideo.id || extractYouTubeId(currentVideo.url));
  } else if (currentType === "embed" || currentType === "iframe") {
    // Hide HTML5 video and YouTube, show Embed player (catalog balancer)
    if (hlsPlayer) { try { hlsPlayer.destroy(); } catch(e) {} hlsPlayer = null; }
    if (videoEl) {
      try {
        videoEl.pause();
        videoEl.removeAttribute("src");
        videoEl.load();
        videoEl.style.display = "none";
      } catch(e) {}
    }
    resetYouTubeDOMTarget();
    if (slot) slot.style.display = "none";
    if (customOverlay) customOverlay.style.display = "none";

    if (embedSlot && embedIframe) {
      embedSlot.style.display = "block";
      if (embedIframe.src !== currentVideo.url) {
        embedIframe.src = currentVideo.url;
      }
    }
    requestWakeLock();
  } else {
    // Native HTML5 / HLS / MP4
    if (embedSlot) { embedSlot.style.display = "none"; if (embedIframe) embedIframe.src = "about:blank"; }
    resetYouTubeDOMTarget();
    if (slot) slot.style.display = "none";
    if (customOverlay) {
      customOverlay.style.display = "flex";
      const botBar = document.getElementById("player-bottom-bar");
      const gestures = document.getElementById("player-gesture-layer");
      if (botBar) botBar.style.display = "flex";
      if (gestures) gestures.style.display = "flex";
    }
    if (videoEl) {
      videoEl.style.display = "block";
      mountHTML5Video(videoEl, currentVideo);
    }
  }
  updateAudioTracksUI();
}
function initYouTubeApi() {
  if (window.YT && window.YT.Player) {
    ytApiReady = true;
    return;
  }
  if (!document.getElementById("yt-iframe-api-script")) {
    const tag = document.createElement("script");
    tag.id = "yt-iframe-api-script";
    tag.src = "https://www.youtube.com/iframe_api";
    document.head.appendChild(tag);
  }
  window.onYouTubeIframeAPIReady = function() {
    ytApiReady = true;
  };
}

function mountYouTubeVideo(videoId) {
  if (!videoId) return;
  const targetTime = computeTargetTime();

  if (ytPlayer && typeof ytPlayer.loadVideoById === "function") {
    try {
      if (currentVideo.playing) {
        ytPlayer.loadVideoById({ videoId: videoId, startSeconds: targetTime });
      } else {
        ytPlayer.cueVideoById({ videoId: videoId, startSeconds: targetTime });
      }
      return;
    } catch(e) {
      ytPlayer = null;
    }
  }

  if (!ytApiReady || !window.YT || !window.YT.Player) {
    initYouTubeApi();
    setTimeout(() => mountYouTubeVideo(videoId), 200);
    return;
  }

  resetYouTubeDOMTarget();
  const slot = document.getElementById("yt-player-slot");
  if (slot) slot.style.display = "block";

  try {
    ytPlayer = new YT.Player("yt-player-target", {
      videoId: videoId,
      playerVars: {
        autoplay: currentVideo.playing ? 1 : 0,
        controls: 1,
        enablejsapi: 1,
        fs: 1,
        iv_load_policy: 3,
        modestbranding: 1,
        playsinline: 1,
        rel: 0,
        origin: window.location.origin
      },
      events: {
        onReady: function(event) {
          window.ytPlayer = event.target;
          ytPlayer = event.target;
          isApplyingRemoteEvent = true;
          event.target.seekTo(targetTime, true);
          if (currentVideo.playing) {
            try { event.target.playVideo(); } catch(e) {}
          } else {
            try { event.target.pauseVideo(); } catch(e) {}
          }
          event.target.setVolume(currentVolume * 100);
          if (isMuted) {
            try { event.target.mute(); } catch(e) {}
          } else {
            try { event.target.unMute(); } catch(e) {}
          }
          updateBufferStatusToServer(false);
          setTimeout(() => { isApplyingRemoteEvent = false; }, 800);
        },
        onStateChange: onYouTubeStateChange
      }
    });
  } catch(err) {
    console.error("Error creating YT.Player:", err);
  }
}

function onYouTubeStateChange(event) {
  const p = event.target || ytPlayer;
  const state = event.data;

  if (state === YT.PlayerState.PLAYING || state === YT.PlayerState.PAUSED || state === 5) {
    isBuffering = false;
    updateBufferStatusToServer(false);
  } else if (state === YT.PlayerState.BUFFERING) {
    isBuffering = true;
    updateBufferStatusToServer(true);
  }

  // If this state change was caused by remote network command, ignore it so we don't echo/loop
  if (isApplyingRemoteEvent) return;

  const curTime = (p && typeof p.getCurrentTime === "function") ? p.getCurrentTime() : 0;

  // User clicked Play inside native YouTube player
  if (state === 0 || (typeof YT !== "undefined" && state === YT.PlayerState.ENDED)) {
    releaseWakeLock();
    onVideoEnded();
  } else if (state === YT.PlayerState.PLAYING) {
    requestWakeLock();
    currentVideo.playing = true;
    currentVideo.time = curTime;
    currentVideo.updated_at = serverNow();
    if (currentRoom) {
      socket.emit("video_play", { room_id: currentRoom, time: curTime, source_sid: socket.id });
    }
    return;
  }

  // User clicked Pause inside native YouTube player
  if (state === YT.PlayerState.PAUSED) {
    releaseWakeLock();
    currentVideo.playing = false;
    currentVideo.time = curTime;
    currentVideo.updated_at = serverNow();
    if (currentRoom) {
      socket.emit("video_pause", { room_id: currentRoom, time: curTime, source_sid: socket.id });
    }
  }
}

function safePlayMedia(el) {
  if (!el) return;
  // STRICT PAUSE GUARD: Never start playback if the video is currently paused!
  if (!currentVideo || !currentVideo.playing) {
    try { el.pause(); } catch(e) {}
    return;
  }
  const p = el.play();
  if (p && typeof p.then === 'function') {
    p.then(() => {
      requestWakeLock();
    }).catch(err => {
      if (err.name === 'NotAllowedError') {
        el.muted = true;
        if (currentVideo && currentVideo.playing) {
          safePlayMedia(el);
        }
      }
    });
  }
}

// NATIVE HTML5 / HLS VIDEO MOUNTING
function mountHTML5Video(videoEl, video) {
  if (hlsPlayer) {
    try { hlsPlayer.destroy(); } catch(e) {}
    hlsPlayer = null;
  }

  videoEl.src = "";
  videoEl.muted = isMuted;
  videoEl.volume = isMuted ? 0 : currentVolume;
  const targetTime = computeTargetTime();

  isApplyingRemoteEvent = true;

  if (video.type === "hls" && typeof Hls !== "undefined" && Hls.isSupported()) {
    hlsPlayer = new Hls({
      enableWorker: true,
      lowLatencyMode: false,
      backBufferLength: 90
    });
    hlsPlayer.on(Hls.Events.AUDIO_TRACKS_UPDATED, function() {
      updateAudioTracksUI();
    });
    hlsPlayer.on(Hls.Events.LEVEL_SWITCHED, function() {
      updateQualityButtonLabel();
    });
    hlsPlayer.loadSource(video.url);
    hlsPlayer.attachMedia(videoEl);
    hlsPlayer.on(Hls.Events.MANIFEST_PARSED, function() {
      updateAudioTracksUI();
      updateQualityLevelsUI();
      if (video.selected_audio && hlsPlayer.audioTracks && hlsPlayer.audioTracks[video.selected_audio]) {
        try { hlsPlayer.audioTrack = video.selected_audio; } catch(e) {}
      }
      if (targetTime > 0) {
        try { videoEl.currentTime = targetTime; } catch(e) {}
      }
      // ONLY start playback if live state is STILL playing!
      if (currentVideo && currentVideo.playing) {
        safePlayMedia(videoEl);
      } else {
        try { videoEl.pause(); } catch(e) {}
      }
      updateBufferStatusToServer(false);
      setTimeout(() => { isApplyingRemoteEvent = false; }, 800);
    });
  } else {
    let playUrl = video.url || "";
    if (playUrl.includes("pixeldrain.com") && !playUrl.includes("/api/proxy/stream")) {
      playUrl = "/api/proxy/stream?url=" + encodeURIComponent(playUrl);
    }
    videoEl.src = playUrl;
    if (targetTime > 0) {
      try { videoEl.currentTime = targetTime; } catch(e) {}
    }
    // ONLY start playback if live state is STILL playing!
    if (currentVideo && currentVideo.playing) {
      safePlayMedia(videoEl);
    } else {
      try { videoEl.pause(); } catch(e) {}
    }
    updateBufferStatusToServer(false);
    setTimeout(() => { isApplyingRemoteEvent = false; }, 800);
  }

  // Hook time updates & buffering
  videoEl.ontimeupdate = onVideoTimeUpdate;
  videoEl.onwaiting = function() {
    isBuffering = true;
    updateBufferStatusToServer(true);
  };
  videoEl.onplaying = function() {
    isBuffering = false;
    updateBufferStatusToServer(false);
  };
  videoEl.oncanplay = function() {
    isBuffering = false;
    updateBufferStatusToServer(false);
  };

  // HTML5 media pipeline events:
  // Capture native player gestures (spacebar on focused video, click on video, media keys, PiP)
  // and sync state reliably across clients without loops.
  videoEl.onplay = function() {
    requestWakeLock();
    updatePlayPauseUI(true);
    flashPlayPauseIcon(true);
    if (!isApplyingRemoteEvent && !videoEl.seeking && currentVideo && !currentVideo.playing) {
      currentVideo.playing = true;
      currentVideo.time = videoEl.currentTime;
      currentVideo.updated_at = serverNow();
      window.currentVideo = currentVideo;
      if (currentRoom) {
        socket.emit("video_play", {
          room_id: currentRoom,
          time: videoEl.currentTime,
          source_sid: socket.id
        });
      }
    }
  };

  videoEl.onpause = function() {
    releaseWakeLock();
    updatePlayPauseUI(false);
    flashPlayPauseIcon(false);
    if (!isApplyingRemoteEvent && !videoEl.seeking && currentVideo && currentVideo.playing) {
      currentVideo.playing = false;
      currentVideo.time = videoEl.currentTime;
      currentVideo.updated_at = serverNow();
      window.currentVideo = currentVideo;
      if (currentRoom) {
        socket.emit("video_pause", {
          room_id: currentRoom,
          time: videoEl.currentTime,
          source_sid: socket.id
        });
      }
    }
  };

  videoEl.onseeked = function() {
    onVideoTimeUpdate();
  };
}

function currentPlayerTime() {
  if (currentType === "youtube") {
    const p = ytPlayer || window.ytPlayer;
    if (p && typeof p.getCurrentTime === "function") {
      try { return p.getCurrentTime() || 0; } catch(e) {}
    }
    return currentVideo.time || 0;
  }
  const el = document.getElementById("rave-video-el");
  return el ? (el.currentTime || 0) : (currentVideo.time || 0);
}

function playerSeekTo(seconds) {
  isApplyingRemoteEvent = true;
  if (currentType === "youtube") {
    const p = ytPlayer || window.ytPlayer;
    if (p && p.seekTo) {
      try { p.seekTo(seconds, true); } catch(e) {}
    }
  } else {
    const el = document.getElementById("rave-video-el");
    if (el) {
      try { el.currentTime = seconds; } catch(e) {}
    }
  }
  setTimeout(() => { isApplyingRemoteEvent = false; }, 500);
}

function setPlayerPlaybackRate(rate) {
  currentPlaybackRate = rate;
  if (currentType === "youtube" && ytPlayer && ytPlayer.setPlaybackRate) {
    try { ytPlayer.setPlaybackRate(rate); } catch(e) {}
  }
  const el = document.getElementById("rave-video-el");
  if (el) el.playbackRate = rate;
}

// ==========================================================================
// 8. MULTI-CITY NETWORK SYNCHRONIZATION ENGINE
// ==========================================================================
function startSyncEngineLoop() {
  if (syncCheckInterval) clearInterval(syncCheckInterval);

  syncCheckInterval = setInterval(function() {
    if (!currentVideo || !currentVideo.playing || isBuffering) return;
    if (Date.now() < ignoreLocalEventsUntil) return;
    if (currentVideo.type === "none") return;

    // Strict physical pause guard: if video is paused, abort sync loop!
    if (currentType !== "youtube") {
      const el = document.getElementById("rave-video-el");
      if (el && el.paused) {
        if (currentVideo.playing && !isApplyingRemoteEvent) {
          currentVideo.playing = false;
          currentVideo.time = el.currentTime;
          currentVideo.updated_at = serverNow();
          if (currentRoom) {
            socket.emit("video_pause", { room_id: currentRoom, time: el.currentTime, source_sid: socket.id });
          }
        }
        return;
      }
    } else {
      const p = ytPlayer || window.ytPlayer;
      if (p && typeof p.getPlayerState === "function") {
        const s = p.getPlayerState();
        if (s === 2) { // 2 = YT.PlayerState.PAUSED
          if (currentVideo.playing && !isApplyingRemoteEvent) {
            currentVideo.playing = false;
            currentVideo.time = currentPlayerTime();
            currentVideo.updated_at = serverNow();
            if (currentRoom) {
              socket.emit("video_pause", { room_id: currentRoom, time: currentVideo.time, source_sid: socket.id });
            }
          }
          return;
        }
      }
    }

    const currentPos = currentPlayerTime();
    const targetPos = computeTargetTime();
    const drift = currentPos - targetPos;
    const absDrift = Math.abs(drift);

    // Update Top Sync Pill
    const syncDot = document.querySelector("#player-top-sync-pill .sync-dot");
    const syncText = document.getElementById("player-top-sync-text");
    if (syncDot && syncText) {
      if (absDrift < 2.5) {
        syncDot.classList.remove("drift");
        syncText.textContent = "Синхронно";
      } else {
        syncDot.classList.add("drift");
        syncText.textContent = `Разница ${absDrift.toFixed(1)}с`;
      }
    }

    // Leader broadcasts current heartbeat time and returns (never self-seeks)
    if (isCurrentRoomLeader && currentRoom && socket.connected) {
      socket.emit("video_heartbeat", { room_id: currentRoom, time: currentPos });
      hideCatchupButton();
      return;
    }

    // Zone 1: Resting Zone (< 3.0s) -> Perfect synchronization across cities
    if (absDrift < 3.0) {
      if (currentPlaybackRate !== 1.0) setPlayerPlaybackRate(1.0);
      hideCatchupButton();
      return;
    }

    // Zone 2: Gentle Glide Zone (3.0s - 7.0s) -> Smooth speed rate adjustment
    if (absDrift <= 7.0) {
      const rate = drift > 0 ? 0.95 : 1.05;
      setPlayerPlaybackRate(rate);
      hideCatchupButton();
      return;
    }

    // Zone 3: Drift Warning (> 7.0s) -> Show non-intrusive catchup sync button in header
    showCatchupButton(absDrift, targetPos);

    // In Zone 3 & 4 (> 7.0s): show catchup pill for intentional user click.
    // NEVER automatically seek in a 1-second interval loop, as that aborts chunk downloads!
    showCatchupButton(absDrift, targetPos);
  }, 1000);
}

function showCatchupButton(driftSec, targetPos) {
  lastLeaderTime = targetPos;
  const pill = document.getElementById("header-catchup-pill");
  const txt = document.getElementById("header-drift-sec");
  if (pill && txt) {
    txt.textContent = `Разница ${driftSec.toFixed(1)}с`;
    pill.style.display = "inline-flex";
  }
}

function hideCatchupButton() {
  const pill = document.getElementById("header-catchup-pill");
  if (pill) pill.style.display = "none";
}

function jumpToLeaderTime() {
  const target = computeTargetTime() || lastLeaderTime;
  if (target > 0) {
    ignoreLocalEventsUntil = Date.now() + 2000;
    isApplyingRemoteEvent = true;
    playerSeekTo(target);
    hideCatchupButton();
    showToast("Синхронизировано!");
    setTimeout(() => { isApplyingRemoteEvent = false; }, 400);
  }
}

function updateBufferStatusToServer(buffering) {
  if (currentRoom) {
    socket.emit("member_buffering", {
      room_id: currentRoom,
      is_buffering: buffering
    });
  }
}

// ==========================================================================

// ==========================================================================
// 8.5. INTERACTIVE MEDIA DETAILS & SEASON / EPISODE / DUBBING PICKER
// ==========================================================================
let currentModalMediaData = null;
let selectedModalSeason = null;
let selectedModalEpisode = null;
let selectedModalDubIndex = 0;

function openMediaDetailsModal(item) {
  closeModal("modal-search-content");
  openModal("modal-media-details");
  const body = document.getElementById("media-modal-body");
  const titleEl = document.getElementById("media-modal-title");
  if (!body) return;

  const title = item.title || "Фильм / Сериал";
  if (titleEl) titleEl.textContent = title;

  body.innerHTML = `
    <div style="display:flex; flex-direction:column; align-items:center; justify-content:center; padding:40px 20px; gap:14px;">
      <div class="vd-spinner"></div>
      <div style="color:var(--text-muted); font-size:0.9rem;">Загрузка доступных озвучек, сезонов и серий...</div>
    </div>
  `;

  const kp = item.kp_id || "";
  const imdb = item.imdb_id || "";
  const detailsUrl = `/api/catalog/details?kp=${encodeURIComponent(kp)}&imdb=${encodeURIComponent(imdb)}`;

  fetch(detailsUrl)
    .then(r => r.json())
    .then(data => {
      if (data.error) {
        body.innerHTML = `
          <div style="text-align:center; padding:30px 10px; color:#ef4444;">
            <div style="font-size:1.5rem; margin-bottom:8px;">⚠️</div>
            <div>${escapeHTML(data.error)}</div>
            <button class="vd-modal-launch-btn" style="margin-top:16px; background:#4b5563;" onclick="closeModal('modal-media-details')">Закрыть</button>
          </div>
        `;
        return;
      }

      currentModalMediaData = {
        ...data,
        title: item.title || data.title || "Видео",
        poster: item.poster || data.poster || "",
        year: item.year || data.year || "",
        rating: item.rating || data.rating || "",
        description: item.description || data.description || "",
        kp_id: kp,
        imdb_id: imdb
      };

      if (currentModalMediaData.type === "series" && currentModalMediaData.seasons && currentModalMediaData.seasons.length) {
        selectedModalSeason = currentModalMediaData.seasons[0].season;
        if (currentModalMediaData.seasons[0].episodes && currentModalMediaData.seasons[0].episodes.length) {
          selectedModalEpisode = currentModalMediaData.seasons[0].episodes[0].episode;
        }
      }
      selectedModalDubIndex = 0;

      renderMediaDetailsModal();
    })
    .catch(() => {
      body.innerHTML = `
        <div style="text-align:center; padding:30px 10px; color:#ef4444;">
          <div>Ошибка загрузки информации о видео</div>
          <button class="vd-modal-launch-btn" style="margin-top:16px; background:#4b5563;" onclick="closeModal('modal-media-details')">Закрыть</button>
        </div>
      `;
    });
}

function renderMediaDetailsModal() {
  const body = document.getElementById("media-modal-body");
  if (!body || !currentModalMediaData) return;

  const d = currentModalMediaData;
  const isSeries = d.type === "series";
  const poster = d.poster || "/static/img/poster-fallback.jpg";
  const ratingBadge = d.rating ? `<span class="media-badge-tag" style="background:rgba(234,179,8,0.2); color:#facc15;">⭐ ${escapeHTML(String(d.rating))}</span>` : "";
  const yearBadge = d.year ? `<span class="media-badge-tag">${escapeHTML(String(d.year))}</span>` : "";
  const typeBadge = isSeries
    ? `<span class="media-badge-tag" style="background:rgba(245,158,11,0.2); color:#f59e0b;">📺 Сериал (${(d.seasons || []).length} сез.)</span>`
    : `<span class="media-badge-tag" style="background:rgba(56,189,248,0.2); color:#38bdf8;">🎬 Фильм</span>`;

  let seasonsHtml = "";
  let episodesHtml = "";
  let audioTracksToRender = [];

  if (isSeries && d.seasons && d.seasons.length) {
    // 1. Seasons Row
    seasonsHtml = `
      <div class="media-section-label">📺 Выберите сезон:</div>
      <div class="seasons-tabs-row">
        ${d.seasons.map(s => `
          <button class="season-tab ${s.season === selectedModalSeason ? 'active' : ''}" onclick="selectModalSeason(${s.season})">
            Сезон ${s.season}
          </button>
        `).join("")}
      </div>
    `;

    // 2. Episodes Row
    const activeSeasonObj = d.seasons.find(s => s.season === selectedModalSeason) || d.seasons[0];
    const episodes = (activeSeasonObj && activeSeasonObj.episodes) ? activeSeasonObj.episodes : [];
    episodesHtml = `
      <div class="media-section-label">🎞️ Серия:</div>
      <div class="episodes-grid-row">
        ${episodes.map(ep => `
          <button class="ep-btn ${ep.episode === selectedModalEpisode ? 'active' : ''}" onclick="selectModalEpisode(${ep.episode})">
            ${ep.episode} сер.
          </button>
        `).join("")}
      </div>
    `;

    // Audio list from active episode or default
    const activeEpObj = episodes.find(e => e.episode === selectedModalEpisode) || episodes[0];
    if (activeEpObj && activeEpObj.audio && activeEpObj.audio.length) {
      audioTracksToRender = activeEpObj.audio;
    }
  } else {
    // Single Movie Audio
    audioTracksToRender = d.audio || [];
  }

  // 3. Dubbings Row
  let dubsHtml = "";
  if (audioTracksToRender.length > 0) {
    dubsHtml = `
      <div class="media-section-label">🎙️ Выберите озвучку / перевод:</div>
      <div class="media-dub-wrap">
        ${audioTracksToRender.map((tr, idx) => `
          <button class="media-dub-pill ${idx === selectedModalDubIndex ? 'active' : ''}" onclick="selectModalDub(${idx})">
            <span>${tr.flag || '🎙️'}</span>
            <span>${escapeHTML(tr.name || 'Дорожка ' + (idx + 1))}</span>
          </button>
        `).join("")}
      </div>
    `;
  }

  // Subtitle info on button
  let launchSubtitle = isSeries ? `Сезон ${selectedModalSeason || 1}, Серия ${selectedModalEpisode || 1}` : "Полная версия";
  if (audioTracksToRender[selectedModalDubIndex]) {
    launchSubtitle += ` • ${audioTracksToRender[selectedModalDubIndex].name}`;
  }

  body.innerHTML = `
    <div class="media-header-card">
      <img src="${escapeHTML(poster)}" class="media-poster-img" onerror="this.src='/static/img/poster-fallback.jpg'">
      <div class="media-meta-col">
        <div class="media-title-main">${escapeHTML(d.title)}</div>
        <div class="media-badges-row">
          ${typeBadge}
          ${yearBadge}
          ${ratingBadge}
        </div>
        ${d.description ? `<div class="media-desc-text">${escapeHTML(d.description)}</div>` : ''}
      </div>
    </div>

    ${seasonsHtml}
    ${episodesHtml}
    ${dubsHtml}

    <button class="vd-modal-launch-btn" onclick="launchMediaFromModal()">
      <span>▶ Смотреть вместе в кинозале</span>
      <span class="vd-modal-launch-sub">${escapeHTML(launchSubtitle)}</span>
    </button>
  `;
}

function selectModalSeason(sNum) {
  selectedModalSeason = sNum;
  if (currentModalMediaData && currentModalMediaData.seasons) {
    const sObj = currentModalMediaData.seasons.find(s => s.season === sNum);
    if (sObj && sObj.episodes && sObj.episodes.length) {
      selectedModalEpisode = sObj.episodes[0].episode;
    }
  }
  selectedModalDubIndex = 0;
  renderMediaDetailsModal();
}

function selectModalEpisode(epNum) {
  selectedModalEpisode = epNum;
  selectedModalDubIndex = 0;
  renderMediaDetailsModal();
}

function selectModalDub(dubIdx) {
  selectedModalDubIndex = dubIdx;
  renderMediaDetailsModal();
}

function launchMediaFromModal() {
  if (!currentModalMediaData) return;
  const d = currentModalMediaData;
  closeModal("modal-media-details");

  const kp = d.kp_id || "";
  const imdb = d.imdb_id || "";
  const isSeries = d.type === "series";
  const title = d.title || "Фильм";
  const s = selectedModalSeason || 1;
  const ep = selectedModalEpisode || 1;
  const dubIdx = selectedModalDubIndex || 0;

  showToast(`🔍 Подключение: ${title}...`);

  const streamUrl = isSeries
    ? `/api/catalog/stream?kp=${encodeURIComponent(kp)}&imdb=${encodeURIComponent(imdb)}&season=${s}&episode=${ep}&title=${encodeURIComponent(title)}`
    : `/api/catalog/stream?kp=${encodeURIComponent(kp)}&imdb=${encodeURIComponent(imdb)}&title=${encodeURIComponent(title)}`;

  fetch(streamUrl)
    .then(r => r.json())
    .then(stream => {
      if (stream && stream.url) {
        startVideoDirectly({
          url: stream.url,
          type: stream.type || "hls",
          title: stream.title || title,
          duration: stream.duration || 0,
          audio_tracks: stream.audio_tracks || d.audio || [],
          subtitles: stream.subtitles || d.subtitles || [],
          kp_id: kp,
          imdb_id: imdb,
          season: isSeries ? s : null,
          episode: isSeries ? ep : null,
          selected_audio: dubIdx
        });
      } else {
        const embedUrl = kp ? `https://api.namy.ws/embed/kp/${kp}` : `https://api.namy.ws/embed/imdb/${imdb}`;
        startVideoDirectly({
          url: embedUrl,
          type: "embed",
          title: title,
          duration: 0
        });
      }
    })
    .catch(() => {
      const embedUrl = kp ? `https://api.namy.ws/embed/kp/${kp}` : `https://api.namy.ws/embed/imdb/${imdb}`;
      startVideoDirectly({
        url: embedUrl,
        type: "embed",
        title: title,
        duration: 0
      });
    });
}

function openEpisodesDrawer() {
  if (currentVideo && (currentVideo.kp_id || currentVideo.imdb_id)) {
    openMediaDetailsModal({
      kp_id: currentVideo.kp_id,
      imdb_id: currentVideo.imdb_id,
      title: currentVideo.title
    });
  } else {
    showToast("Для данного видео список серий не найден");
  }
}

// ==========================================================================
// 9. UNIVERSAL SEARCH & MEDIA LAUNCHING
// ==========================================================================
function submitUniversalSearch() {
  const input = document.getElementById("universal-search-input");
  if (!input) return;
  let q = input.value.trim();
  if (!q) return;

  // 1. Pixeldrain Link (flexible regex for pixeldrain.com, xeldrain.com, pd.to, /u/, /api/file/)
  const pdMatch = q.match(/(?:pixeldrain\.com|xeldrain\.com|pd\.to)\/(?:u\/|api\/file\/)?([a-zA-Z0-9_-]{6,16})/i);
  if (pdMatch) {
    const fileId = pdMatch[1];
    const rawUrl = "https://pixeldrain.com/api/file/" + fileId;
    const proxiedUrl = "/api/proxy/stream?url=" + encodeURIComponent(rawUrl);
    showToast("💡 Совет: для экономии лимита сервера можно скачать видео и открыть через «📁 Диск / Файл» — 0 МБ трафика сервера!", 7000);
    startVideoDirectly({
      url: proxiedUrl,
      type: "mp4",
      title: "Pixeldrain Видео",
      duration: 0
    });
    input.value = "";
    return;
  }

  // 2. YouTube Link
  const ytId = extractYouTubeId(q);
  if (ytId) {
    let ytUrl = q;
    if (!ytUrl.startsWith("http://") && !ytUrl.startsWith("https://")) {
      ytUrl = "https://" + ytUrl;
    }
    startVideoDirectly({
      url: ytUrl,
      id: ytId,
      type: "youtube",
      title: "YouTube видео",
      duration: 0
    });
    input.value = "";
    return;
  }

  // 3. Direct HLS or MP4 stream
  if (q.includes(".m3u8") || q.includes(".mp4") || q.startsWith("http://") || q.startsWith("https://")) {
    let sUrl = q;
    if (!sUrl.startsWith("http://") && !sUrl.startsWith("https://")) {
      sUrl = "https://" + sUrl;
    }
    startVideoDirectly({
      url: sUrl,
      type: sUrl.includes(".m3u8") ? "hls" : "mp4",
      title: "Прямой видеопоток",
      duration: 0
    });
    input.value = "";
    return;
  }

  // 4. Movie / Series title search
  openSearchModalTab("search", q);
  input.value = "";
}

function startVideoDirectly(payload) {
  const vidObj = {
    url: payload.url,
    id: payload.id || "",
    type: payload.type || "mp4",
    title: payload.title || "Видео",
    duration: payload.duration || 0,
    playing: true,
    time: 0,
    updated_at: serverNow(),
    audio_tracks: payload.audio_tracks || [],
    subtitles: payload.subtitles || [],
    kp_id: payload.kp_id || "",
    imdb_id: payload.imdb_id || "",
    season: payload.season || null,
    episode: payload.episode || null,
    selected_audio: payload.selected_audio || 0
  };
  if (currentRoom) {
    showRoomView();
    renderPlayer(vidObj);
    socket.emit("change_video", {
      room_id: currentRoom,
      ...vidObj
    });
    showToast(`🎬 Запущено: ${payload.title || 'Видео'}`);
  } else {
    showToast("Создание комнаты совместного просмотра...");
    socket.emit("create_room", {
      title: payload.title || "Совместный просмотр",
      name: payload.title || "Совместный просмотр",
      user: { id: currentUser.id, name: currentUser.username, avatar: currentUser.avatar }
    });
    socket.once("room_created", function(data) {
      socket.emit("change_video", {
        room_id: data.room.id,
        ...vidObj
      });
    });
  }
}

// LOCAL DISK 0s LAUNCH
function openDiskModal() {
  openModal("modal-disk-file");
  loadRecentDiskFiles();
}

function submitDiskPathFromModal() {
  const input = document.getElementById("disk-path-input");
  const rawPath = input ? input.value.trim() : "";
  if (!rawPath) {
    showToast("Укажите путь к видеофайлу на диске");
    return;
  }
  launchDiskPath(rawPath);
}

function launchDiskPath(path) {
  showToast("Открытие файла с диска за 0 сек...");
  fetch("/api/open_disk_path", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ path: path, file_path: path })
  })
  .then(r => r.json())
  .then(data => {
    if (data.status === "ok" || data.success) {
      closeModal("modal-disk-file");
      startVideoDirectly({
        url: data.stream_url || data.url,
        type: "mp4",
        title: data.title || "Локальное видео",
        duration: data.duration || 0
      });
      showToast(`🎬 Файл открыт: ${data.title || "Видео"}`);
    } else {
      showToast(data.message || data.error || "Файл не найден на диске");
    }
  })
  .catch(() => {
    showToast("Ошибка при открытии файла с диска");
  });
}

function loadRecentDiskFiles() {
  fetch("/api/recent_disk_files")
    .then(r => r.json())
    .then(data => {
      const list = data.files || [];
      const container = document.getElementById("disk-recent-files");
      if (!container) return;
      if (!list.length) {
        container.innerHTML = `<span style="color:var(--text-muted); font-size:0.8rem;">Нет ранее открытых файлов на диске</span>`;
        return;
      }
      container.innerHTML = "";
      list.slice(0, 5).forEach(f => {
        const item = document.createElement("div");
        item.style.cssText = "display:flex; justify-content:space-between; align-items:center; background:var(--bg-card); padding:8px 12px; border-radius:8px; cursor:pointer;";
        item.innerHTML = `<span style="font-weight:500; font-size:0.82rem; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; max-width:80%;">${escapeHTML(f.title || f.filename || 'Видео')}</span><button class="header-btn" style="padding:4px 8px; font-size:0.72rem;">Запустить</button>`;
        item.onclick = () => launchDiskPath(f.path || f.url);
        container.appendChild(item);
      });
    })
    .catch(() => {});
}

function handleNativeFileSelect(e) {
  const file = e.target.files && e.target.files[0];
  if (!file) return;
  handleFileUniversal(file);
  e.target.value = "";
}

function handleFileUniversal(file) {
  showToast(`🔍 Проверяем файл на ПК: ${file.name}...`);
  fetch(`/api/find_disk_file?filename=${encodeURIComponent(file.name)}&size=${file.size || 0}`)
    .then(r => r.json())
    .then(findRes => {
      const diskPath = findRes.file_path || findRes.path;
      if (diskPath) {
        launchDiskPath(diskPath);
      } else {
        showToast("Файл не найден на локальном диске ПК");
      }
    })
    .catch(() => {
      showToast("Ошибка поиска файла на ПК");
    });
}

function initDragAndDrop() {
  window.addEventListener("dragover", e => e.preventDefault(), false);
  window.addEventListener("drop", e => e.preventDefault(), false);

  const stage = document.getElementById("player-stage-wrap");
  const overlay = document.getElementById("player-drop-overlay");

  if (stage && overlay) {
    stage.addEventListener("dragenter", () => overlay.classList.add("active"));
    stage.addEventListener("dragleave", e => {
      if (e.relatedTarget === null || !stage.contains(e.relatedTarget)) {
        overlay.classList.remove("active");
      }
    });
    stage.addEventListener("drop", e => {
      overlay.classList.remove("active");
      const dt = e.dataTransfer;
      if (dt && dt.files && dt.files.length > 0) {
        handleFileUniversal(dt.files[0]);
      }
    });
  }
}

// SEARCH MODAL
function openSearchModalTab(source, query) {
  openModal("modal-search-content");
  const titleEl = document.getElementById("search-modal-title");
  const input = document.getElementById("modal-search-input");
  if (titleEl) {
    titleEl.textContent = source === "movies" ? "Каталог фильмов и сериалов" : (source === "youtube" ? "Поиск YouTube" : "Каталог видео");
  }
  if (input) {
    input.value = query || "";
  }
  executeModalSearch();
}

function executeModalSearch() {
  const input = document.getElementById("modal-search-input");
  const container = document.getElementById("modal-search-results");
  if (!container) return;
  let q = input ? input.value.trim() : "";

  if (q.includes("pixeldrain.com/u/")) {
    q = q.replace("pixeldrain.com/u/", "pixeldrain.com/api/file/");
  }

  // If a direct URL is pasted into search modal, launch it directly!
  if (q.startsWith("http://") || q.startsWith("https://")) {
    closeModal("modal-search-content");
    startVideoDirectly({
      url: q,
      type: q.includes(".m3u8") ? "hls" : "mp4",
      title: "Прямое видео",
      duration: 0
    });
    if (input) input.value = "";
    return;
  }

  container.innerHTML = `<span style="grid-column: 1/-1; text-align:center; padding:20px; color:var(--text-muted);">Поиск...</span>`;

  fetch(`/api/search?q=${encodeURIComponent(q)}`)
    .then(r => r.json())
    .then(data => {
      const results = data.results || [];
      if (!results.length) {
        container.innerHTML = `<span style="grid-column: 1/-1; text-align:center; padding:20px; color:var(--text-muted);">Ничего не найдено</span>`;
        return;
      }
      container.innerHTML = "";
      results.forEach(res => {
        const card = document.createElement("div");
        card.style.cssText = "background:var(--bg-card); border:1px solid var(--border-color); border-radius:10px; padding:10px; cursor:pointer; display:flex; flex-direction:column; gap:8px; transition: transform 0.15s, border-color 0.15s;";
        card.onmouseover = () => { card.style.borderColor = "var(--primary)"; };
        card.onmouseout = () => { card.style.borderColor = "var(--border-color)"; };

        const poster = res.poster || "/static/img/poster-fallback.jpg";
        const yearBadge = res.year ? `<span style="font-size:0.7rem; color:var(--text-muted);">${escapeHTML(res.year)}</span>` : "";
        const typeBadge = res.type === "series" ? `<span style="font-size:0.68rem; background:rgba(245,158,11,0.2); color:#f59e0b; padding:1px 5px; border-radius:4px; font-weight:600;">Сериал</span>` : (res.type === "movie" ? `<span style="font-size:0.68rem; background:rgba(56,189,248,0.2); color:#38bdf8; padding:1px 5px; border-radius:4px; font-weight:600;">Фильм</span>` : "");

        card.innerHTML = `
          <div style="width:100%; height:130px; border-radius:6px; overflow:hidden; background:#000; position:relative;">
            <img src="${escapeHTML(poster)}" style="width:100%; height:100%; object-fit:cover;" onerror="this.src='/static/img/poster-fallback.jpg'">
            <div style="position:absolute; top:6px; right:6px; display:flex; gap:4px;">${typeBadge}</div>
          </div>
          <div style="display:flex; justify-content:space-between; align-items:center;">
            <span style="font-weight:600; font-size:0.85rem; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; flex:1;">${escapeHTML(res.title || 'Видео')}</span>
            ${yearBadge}
          </div>
        `;
        card.onclick = () => {
          if (res.url) {
            closeModal("modal-search-content");
            startVideoDirectly({
              url: res.url,
              id: res.id || "",
              type: res.type || (res.url.includes(".m3u8") ? "hls" : "mp4"),
              title: res.title || "Видео",
              duration: res.duration || 0
            });
          } else if (res.teleportal) {
            closeModal("modal-search-content");
            playTeleportalShow(res);
          } else if (res.kp_id || res.imdb_id) {
            openMediaDetailsModal(res);
          } else {
            showToast("Не удалось определить поток видео");
          }
        };
        container.appendChild(card);
      });
    })
    .catch(() => {
      container.innerHTML = `<span style="grid-column: 1/-1; text-align:center; padding:20px; color:#ef4444;">Ошибка поиска</span>`;
    });
}

function playCatalogMedia(item) {
  showToast(`🔍 Загрузка: ${item.title || 'Фильм'}...`);
  const kp = item.kp_id || "";
  const imdb = item.imdb_id || "";
  const isSeries = item.type === "series";

  const streamUrl = isSeries
    ? `/api/catalog/stream?kp=${encodeURIComponent(kp)}&imdb=${encodeURIComponent(imdb)}&season=1&episode=1`
    : `/api/catalog/stream?kp=${encodeURIComponent(kp)}&imdb=${encodeURIComponent(imdb)}`;

  fetch(streamUrl)
    .then(r => r.json())
    .then(stream => {
      if (stream && stream.url) {
        startVideoDirectly({
          url: stream.url,
          type: stream.type || "hls",
          title: stream.title || item.title || "Фильм",
          duration: stream.duration || 0,
          audio_tracks: stream.audio_tracks || []
        });
      } else {
        // Fallback to embed balancer if stream extraction returns none
        const embedUrl = kp ? `https://api.namy.ws/embed/kp/${kp}` : `https://api.namy.ws/embed/imdb/${imdb}`;
        startVideoDirectly({
          url: embedUrl,
          type: "embed",
          title: item.title || "Фильм",
          duration: 0
        });
      }
    })
    .catch(() => {
      const embedUrl = kp ? `https://api.namy.ws/embed/kp/${kp}` : `https://api.namy.ws/embed/imdb/${imdb}`;
      startVideoDirectly({
        url: embedUrl,
        type: "embed",
        title: item.title || "Фильм",
        duration: 0
      });
    });
}

function playTeleportalShow(item) {
  const tp = item.teleportal || {};
  showToast(`🔍 Загрузка: ${item.title}...`);
  fetch(`/api/project?type=${tp.type || 'show'}&channel=${tp.channel || 'stb'}&project=${tp.project || 'supermama'}`)
    .then(r => r.json())
    .then(data => {
      if (data.seasons && data.seasons.length && data.seasons[0].episodes && data.seasons[0].episodes.length) {
        const ep = data.seasons[0].episodes[0];
        if (ep.hash) {
          fetch(`/api/resolve_hash?hash=${ep.hash}`)
            .then(r => r.json())
            .then(res => {
              if (res && res.url) {
                startVideoDirectly({
                  url: res.url,
                  type: "hls",
                  title: `${item.title} - ${ep.title}`,
                  duration: ep.duration || 0
                });
              }
            });
        }
      }
    })
    .catch(() => {
      showToast("Не удалось загрузить выпуск");
    });
}
// 10. CHAT & MESSAGING
// ==========================================================================
const seenChatMsgIds = new Set();

function sendChatMessage() {
  const input = document.getElementById("chat-input-field");
  if (!input) return;
  const text = input.value.trim();
  if (!text || !currentRoom) return;

  const userObj = {
    id: currentUser.id || "u_" + Math.random().toString(36).substring(2, 9),
    name: currentUser.username || currentUser.name || "Гость",
    avatar: currentUser.avatar || ""
  };

  const payload = {
    room_id: currentRoom,
    text: text,
    message: text,
    author: userObj.name,
    avatar: userObj.avatar,
    user: userObj
  };

  // Send chat message to server
  socket.emit("send_message", payload);

  input.value = "";
  try { input.focus(); } catch(e) {}
}

function appendChatMessage(msg) {
  const container = document.getElementById("chat-messages");
  if (!container || !msg) return;

  const msgText = msg.text || msg.message || "";
  if (!msgText.trim()) return;

  const msgId = msg.id || (msgText + "_" + (msg.ts || msg.time || ""));
  if (msgId && seenChatMsgIds.has(msgId)) return;
  if (msgId) seenChatMsgIds.add(msgId);

  const row = document.createElement("div");
  row.className = "chat-msg-row";

  const author = msg.author || msg.user_name || msg.name || (msg.user && (msg.user.name || msg.user.username)) || "Участник";
  const avatar = msg.avatar || msg.sender_avatar || (msg.user && msg.user.avatar) || "";
  let timeStr = "";
  if (msg.time && typeof msg.time === "string" && msg.time.includes(":")) {
    timeStr = msg.time;
  } else if (msg.ts) {
    timeStr = formatTimeClock(msg.ts);
  } else {
    timeStr = formatTimeClock(Date.now());
  }
  const initial = (author.charAt(0) || "U").toUpperCase();

  const isVika = author.toLowerCase().includes("вик") || author.toLowerCase().includes("ria");
  const authorColor = isVika ? "#f472b6" : "#38bdf8";

  const avatarHtml = avatar 
    ? `<img src="${escapeHTML(avatar)}" alt="${escapeHTML(author)}">`
    : initial;

  row.innerHTML = `
    <div class="chat-msg-avatar" style="${isVika ? 'background: linear-gradient(135deg, #ec4899 0%, #8b5cf6 100%);' : ''}">${avatarHtml}</div>
    <div class="chat-msg-bubble">
      <div class="chat-msg-header">
        <span class="chat-msg-author" style="color: ${authorColor};">${escapeHTML(author)}</span>
        <span class="chat-msg-time">${escapeHTML(timeStr)}</span>
      </div>
      <div class="chat-msg-text">${escapeHTML(msgText)}</div>
    </div>
  `;

  container.appendChild(row);
  container.scrollTop = container.scrollHeight;
}

// ==========================================================================
// 11. AUTH & USER PROFILE MODAL
// ==========================================================================
function attemptSelfHealSession() {
  const savedProfile = localStorage.getItem("vd_user_profile");
  const savedCreds = localStorage.getItem("vd_user_credentials");
  if (!savedProfile && !savedCreds) return;

  let profile = null;
  try { profile = JSON.parse(savedProfile); } catch(e) {}
  let creds = null;
  try { creds = JSON.parse(savedCreds); } catch(e) {}

  if (!profile && !creds) return;

  fetch("/api/auth/self_heal", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ profile: profile, creds: creds })
  })
  .then(r => r.json())
  .then(res => {
    if (res && res.success && res.user && res.token) {
      currentUser = res.user;
      currentUser.isGuest = false;
      localStorage.setItem("vd_token", res.token);
      localStorage.setItem("vd_user_profile", JSON.stringify(res.user));
      updateHeaderUserAvatar();
      if (socket && socket.connected) {
        socket.emit("identify_user", { user_id: currentUser.id });
      }
      if (typeof fetchFriendsActivity === "function") {
        fetchFriendsActivity();
      }
    }
  })
  .catch(() => {});
}

function loadAuthSession() {
  const token = localStorage.getItem("vd_token");
  const headers = {};
  if (token) headers["Authorization"] = "Bearer " + token;

  fetch("/api/auth/me", { headers })
    .then(r => r.json())
    .then(data => {
      if (data && data.user) {
        currentUser = data.user;
        currentUser.isGuest = false;
        localStorage.setItem("vd_user_profile", JSON.stringify(data.user));
        updateHeaderUserAvatar();
        if (socket && socket.connected) {
          socket.emit("identify_user", { user_id: currentUser.id });
        }
        if (typeof fetchFriendsActivity === "function") {
          fetchFriendsActivity();
        }
      } else {
        attemptSelfHealSession();
      }
    })
    .catch(() => {
      attemptSelfHealSession();
    });
}

function updateHeaderUserAvatar() {
  const nameEl = document.getElementById("header-username-text");
  const circleEl = document.getElementById("header-avatar-circle");
  if (nameEl) nameEl.textContent = currentUser.username || "Войти";
  if (circleEl) {
    if (currentUser.avatar) {
      circleEl.innerHTML = `<img src="${escapeHTML(currentUser.avatar)}">`;
    } else {
      circleEl.textContent = (currentUser.username ? currentUser.username.charAt(0) : "U").toUpperCase();
    }
  }
}

function openAuthOrProfileModal() {
  openModal("modal-auth-profile");
  const body = document.getElementById("auth-modal-body");
  const title = document.getElementById("auth-modal-title");
  if (!body) return;

  if (currentUser && !currentUser.isGuest) {
    // Show Profile, Avatar Upload & Statistics
    title.textContent = "Мой профиль и аватарка";
    const userAv = currentUser.avatar
      ? `<img src="${escapeHTML(currentUser.avatar)}" style="width:100%; height:100%; object-fit:cover;">`
      : (currentUser.username ? currentUser.username.charAt(0).toUpperCase() : "U");

    body.innerHTML = `
      <!-- User Info & Avatar Header -->
      <div style="display:flex; align-items:center; gap:16px; padding-bottom:14px; border-bottom:1px solid var(--border-color);">
        <div style="position:relative; cursor:pointer;" onclick="document.getElementById('profile-avatar-file').click()" title="Нажмите, чтобы сменить фото">
          <div class="header-avatar" id="profile-modal-avatar-preview" style="width:62px; height:62px; font-size:1.5rem; border:2px solid var(--accent); box-shadow:0 0 16px rgba(168,85,247,0.35); overflow:hidden;">
            ${userAv}
          </div>
          <div style="position:absolute; bottom:-3px; right:-3px; background:var(--accent); width:22px; height:22px; border-radius:50%; display:flex; align-items:center; justify-content:center; font-size:11px; border:2px solid #0f0f13; box-shadow:0 2px 6px rgba(0,0,0,0.5);">
            📷
          </div>
        </div>
        <div style="flex:1; min-width:0;">
          <div style="display:flex; align-items:center; gap:6px;">
            <input type="text" id="profile-display-name-input" value="${escapeHTML(currentUser.display_name || currentUser.username)}" placeholder="Ваше имя / никнейм" style="background:var(--bg-card); border:1px solid var(--border-color); border-radius:6px; padding:6px 10px; color:#fff; font-size:0.95rem; font-weight:700; width:100%; max-width:180px;">
            <button class="header-btn" onclick="saveDisplayNameFromUI()" title="Сохранить имя" style="padding:6px 10px; font-size:0.75rem;">💾 Сохранить</button>
          </div>
          <div style="font-size:0.78rem; color:var(--text-muted); margin-top:4px;">Логин: @${escapeHTML(currentUser.username)}</div>
        </div>
      </div>

      <!-- Avatar Change Controls -->
      <div style="margin-top:14px; padding:12px; background:rgba(255,255,255,0.03); border-radius:10px; border:1px solid var(--border-color);">
        <div style="font-size:0.82rem; font-weight:700; color:var(--text-secondary); margin-bottom:8px; display:flex; align-items:center; justify-content:space-between;">
          <span>Смена аватарки</span>
          <span style="font-size:0.72rem; color:var(--text-muted);">JPG, PNG, WEBP, GIF</span>
        </div>

        <!-- Hidden Native File Input -->
        <input type="file" id="profile-avatar-file" style="display:none;" accept="image/*" onchange="uploadAvatarFile(this)">

        <div style="display:flex; gap:8px;">
          <button class="btn-hero-create" onclick="document.getElementById('profile-avatar-file').click()" style="flex:1; padding:8px 12px; font-size:0.82rem; justify-content:center;">
            📁 Загрузить фото с устройства
          </button>
        </div>

        <!-- URL Input -->
        <div style="display:flex; gap:6px; margin-top:10px;">
          <input type="text" id="avatar-url-input" placeholder="Или ссылка на картинку..." style="flex:1; background:var(--bg-card); border:1px solid var(--border-color); border-radius:8px; padding:7px 10px; font-size:0.8rem; color:#fff;">
          <button class="header-btn" onclick="saveAvatarFromUrl()" style="padding:7px 12px; font-size:0.8rem; white-space:nowrap;">Сохранить</button>
        </div>

        <!-- Stylish Preset Avatars -->
        <div style="margin-top:12px;">
          <div style="font-size:0.75rem; color:var(--text-muted); margin-bottom:6px;">Или выберите пресет в 1 клик:</div>
          <div style="display:flex; gap:8px; overflow-x:auto; padding-bottom:4px;">
            ${getAvatarPresetsHtml()}
          </div>
        </div>
      </div>

      <!-- Watch Statistics -->
      <div style="display:grid; grid-template-columns:1fr 1fr; gap:10px; margin-top:14px;">
        <div style="background:var(--bg-card); padding:10px; border-radius:10px; text-align:center;">
          <div style="font-size:1.2rem; font-weight:800; color:#38bdf8;" id="stat-watch-hours">~</div>
          <div style="font-size:0.72rem; color:var(--text-muted);">Часов просмотра</div>
        </div>
        <div style="background:var(--bg-card); padding:10px; border-radius:10px; text-align:center;">
          <div style="font-size:1.2rem; font-weight:800; color:#4ade80;" id="stat-movies-count">~</div>
          <div style="font-size:0.72rem; color:var(--text-muted);">Фильмов и серий</div>
        </div>
      </div>

      <button class="header-btn" onclick="logoutUser()" style="width:100%; justify-content:center; color:#f87171; margin-top:12px; font-size:0.82rem;">
        Выйти из аккаунта
      </button>
    `;
    fetch("/api/auth/profile")
      .then(r => r.json())
      .then(d => {
        if (d && d.stats) {
          const h = (d.stats.total_watch_seconds / 3600).toFixed(1);
          const elH = document.getElementById("stat-watch-hours");
          const elC = document.getElementById("stat-movies-count");
          if (elH) elH.textContent = h;
          if (elC) elC.textContent = d.stats.movies_watched || 0;
        }
      })
      .catch(() => {});
  } else {
    // Show Login / Registration
    title.textContent = "Вход / Регистрация";
    body.innerHTML = `
      <div style="display:flex; flex-direction:column; gap:12px;">
        <input type="text" id="auth-input-username" placeholder="Имя пользователя" style="background:var(--bg-card); border:1px solid var(--border-color); border-radius:8px; padding:10px 14px; color:#fff;">
        <input type="password" id="auth-input-password" placeholder="Пароль" style="background:var(--bg-card); border:1px solid var(--border-color); border-radius:8px; padding:10px 14px; color:#fff;">
        <div style="display:flex; gap:10px; margin-top:6px;">
          <button class="header-btn active" onclick="loginUser()" style="flex:1; justify-content:center; padding:10px;">Войти</button>
          <button class="header-btn" onclick="registerUser()" style="flex:1; justify-content:center; padding:10px;">Регистрация</button>
        </div>
      </div>
    `;
  }
}

function getAvatarPresetsHtml() {
  const presets = [
    { name: "Neon Cinema", url: "https://images.unsplash.com/photo-1534447677768-be436bb09401?w=160&auto=format&fit=crop&q=80" },
    { name: "Cyberpunk", url: "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=160&auto=format&fit=crop&q=80" },
    { name: "Guy Portrait", url: "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=160&auto=format&fit=crop&q=80" },
    { name: "Aesthetic Cat", url: "https://images.unsplash.com/photo-1514888286974-6c03e2ca1dba?w=160&auto=format&fit=crop&q=80" },
    { name: "Cosmos", url: "https://images.unsplash.com/photo-1518709268805-4e9042af9f23?w=160&auto=format&fit=crop&q=80" },
    { name: "Neon Heart", url: "https://images.unsplash.com/photo-1518199266791-5375a83190b7?w=160&auto=format&fit=crop&q=80" },
    { name: "Popcorn", url: "https://images.unsplash.com/photo-1578849278619-e73505e9610f?w=160&auto=format&fit=crop&q=80" },
    { name: "Night City", url: "https://images.unsplash.com/photo-1519501025264-65ba15a82390?w=160&auto=format&fit=crop&q=80" }
  ];

  return presets.map(p => `
    <button class="preset-avatar-btn" onclick="applyPresetAvatar('${p.url}')" title="${p.name}">
      <img src="${p.url}" alt="${p.name}">
    </button>
  `).join("");
}

function uploadAvatarFile(input) {
  if (!input || !input.files || !input.files[0]) return;
  const file = input.files[0];
  if (file.size > 15 * 1024 * 1024) {
    showToast("Файл слишком большой (макс 15 МБ)");
    return;
  }
  showToast("Загрузка и обработка аватарки...");
  const formData = new FormData();
  formData.append("avatar", file);

  fetch("/api/auth/avatar", {
    method: "POST",
    body: formData
  })
  .then(r => r.json())
  .then(data => {
    if (data.success && data.avatar) {
      currentUser.avatar = data.avatar;
      updateHeaderUserAvatar();
      updateProfileModalAvatarPreview(data.avatar);
      showToast("✨ Аватарка успешно обновлена!");
      if (typeof fetchFriendsActivity === "function") fetchFriendsActivity();
    } else {
      showToast(data.error || "Ошибка загрузки аватарки");
    }
  })
  .catch(() => showToast("Ошибка сети при загрузке"));
}

function saveAvatarFromUrl() {
  const input = document.getElementById("avatar-url-input");
  if (!input) return;
  const url = input.value.trim();
  if (!url) {
    showToast("Введите ссылку на картинку");
    return;
  }
  applyPresetAvatar(url);
  input.value = "";
}

function applyPresetAvatar(url) {
  if (!url) return;
  showToast("Сохранение аватарки...");
  fetch("/api/auth/avatar", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ avatar_url: url })
  })
  .then(r => r.json())
  .then(data => {
    if (data.success && data.avatar) {
      currentUser.avatar = data.avatar;
      updateHeaderUserAvatar();
      updateProfileModalAvatarPreview(data.avatar);
      showToast("✨ Аватарка успешно обновлена!");
      if (typeof fetchFriendsActivity === "function") fetchFriendsActivity();
    } else {
      showToast(data.error || "Не удалось сохранить аватар");
    }
  })
  .catch(() => showToast("Ошибка сети"));
}

function updateProfileModalAvatarPreview(avatarUrl) {
  const el = document.getElementById("profile-modal-avatar-preview");
  if (el) {
    el.innerHTML = `<img src="${escapeHTML(avatarUrl)}" style="width:100%; height:100%; object-fit:cover;">`;
  }
}

function saveDisplayNameFromUI() {
  const input = document.getElementById("profile-display-name-input");
  if (!input) return;
  const newName = input.value.trim();
  if (!newName) {
    showToast("Имя не может быть пустым");
    return;
  }
  fetch("/api/auth/profile", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ display_name: newName })
  })
  .then(r => r.json())
  .then(data => {
    if (data.success && data.user) {
      currentUser.display_name = data.user.display_name;
      updateHeaderUserAvatar();
      showToast(`Имя изменено на «${currentUser.display_name}»!`);
      if (typeof fetchFriendsActivity === "function") fetchFriendsActivity();
    } else {
      showToast(data.error || "Ошибка сохранения имени");
    }
  })
  .catch(() => showToast("Ошибка сети"));
}

function loginUser() {
  const u = document.getElementById("auth-input-username").value.trim();
  const p = document.getElementById("auth-input-password").value.trim();
  if (!u || !p) { showToast("Заполните имя и пароль"); return; }
  fetch("/api/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username: u, password: p })
  })
  .then(r => r.json())
  .then(data => {
    if (data.success || data.user) {
      if (data.token) {
        localStorage.setItem("vd_token", data.token);
      }
      currentUser = data.user;
      localStorage.setItem("vd_user_profile", JSON.stringify(data.user));
      localStorage.setItem("vd_user_credentials", JSON.stringify({ username: u, password: p }));
      currentUser.isGuest = false;
      updateHeaderUserAvatar();
      closeModal("modal-auth-profile");
      showToast(`Добро пожаловать, ${currentUser.username}!`);
      if (socket && socket.connected) {
        socket.emit("identify_user", { user_id: currentUser.id });
      }
      if (typeof fetchFriendsActivity === "function") {
        fetchFriendsActivity();
      }
    } else {
      showToast(data.message || data.error || "Ошибка входа");
    }
  })
  .catch(() => showToast("Ошибка сети"));
}

function registerUser() {
  const u = document.getElementById("auth-input-username").value.trim();
  const p = document.getElementById("auth-input-password").value.trim();
  if (!u || !p) { showToast("Заполните имя и пароль"); return; }
  fetch("/api/auth/register", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username: u, password: p, display_name: u })
  })
  .then(r => r.json())
  .then(data => {
    if (data.success || data.user) {
      if (data.token) {
        localStorage.setItem("vd_token", data.token);
      }
      currentUser = data.user;
      localStorage.setItem("vd_user_profile", JSON.stringify(data.user));
      localStorage.setItem("vd_user_credentials", JSON.stringify({ username: u, password: p }));
      currentUser.isGuest = false;
      updateHeaderUserAvatar();
      closeModal("modal-auth-profile");
      showToast(`Аккаунт ${currentUser.username} зарегистрирован!`);
      if (socket && socket.connected) {
        socket.emit("identify_user", { user_id: currentUser.id });
      }
      if (typeof fetchFriendsActivity === "function") {
        fetchFriendsActivity();
      }
    } else {
      showToast(data.message || data.error || "Ошибка регистрации");
    }
  })
  .catch(() => showToast("Ошибка сети"));
}

function logoutUser() {
  localStorage.removeItem("vd_token");
  fetch("/api/auth/logout", { method: "POST" })
    .finally(() => {
      currentUser = {
        id: "u_" + Math.random().toString(36).substring(2, 10),
        username: "Гость_" + Math.floor(100 + Math.random() * 900),
        display_name: "Гость",
        avatar: "",
        isGuest: true
      };
      updateHeaderUserAvatar();
      closeModal("modal-auth-profile");
      showToast("Вы вышли из аккаунта");
      if (typeof fetchFriendsActivity === "function") {
        fetchFriendsActivity();
      }
    });
}

// ==========================================================================
// 12. SOCKET.IO EVENT LISTENERS
// ==========================================================================
socket.on("connect", function() {
  if (currentUser && !currentUser.isGuest) {
    socket.emit("identify_user", { user_id: currentUser.id });
  }
  if (currentRoom) {
    socket.emit("join_room", {
      room_id: currentRoom,
      user: { id: currentUser.id, name: currentUser.username, avatar: currentUser.avatar }
    });
    socket.emit("request_sync", { room_id: currentRoom });
  }
});

socket.on("room_created", function(data) {
  if (data && data.room) {
    if (data.code) currentRoomCode = data.code;
    joinRoomDirectly(data.room.id, data.code || "");
    showToast(data.code ? `🔒 Приватная комната создана!` : `Комната создана!`);
  }
});

socket.on("room_reaction", function(data) {
  if (data && data.emoji) {
    spawnFloatingEmoji(data.emoji);
  }
});

socket.on("room_joined", function(data) {
  currentRoomData = data.room;
  currentRoom = data.room.id;
  if (data.code) currentRoomCode = data.code;
  isCurrentRoomLeader = !!data.is_leader;
  showRoomView();
  updateRoomHeaderInfo(currentRoom);
  if (data.room && data.room.video && data.room.video.url) {
    renderPlayer(data.room.video);
  }
  socket.emit("request_sync", { room_id: currentRoom });
});

socket.on("room_error", function(data) {
  const msg = (data && data.message) || "Ошибка комнаты";
  showToast("🔒 " + msg);
  if (msg.toLowerCase().includes("код") || msg.toLowerCase().includes("секретный")) {
    const entered = prompt("🔒 Эта комната приватная. Введите секретный код доступа (PIN):");
    if (entered) {
      currentRoomCode = entered.trim();
      joinRoomDirectly(currentRoom, currentRoomCode);
    } else {
      showLobbyView();
    }
  } else {
    showLobbyView();
  }
});

socket.on("room_state", function(data) {
  if (data.room && data.room.id) {
    if (!currentRoom) currentRoom = data.room.id;
    if (data.room.id !== currentRoom) return;
    currentRoomData = data.room;
  }
  if (data.leader_sid) {
    isCurrentRoomLeader = (data.leader_sid === socket.id);
  } else if (data.is_leader !== undefined) {
    isCurrentRoomLeader = !!data.is_leader;
  }
  if (data.server_time) handleServerTimeSample(data.server_time);
  if (data.video) {
    renderPlayer(data.video);
  }
  if (data.chat && Array.isArray(data.chat)) {
    const box = document.getElementById("chat-messages");
    if (box) {
      box.innerHTML = "";
      data.chat.forEach(msg => appendChatMessage(msg));
    }
  }
  if (data.members) {
    renderRoomMembers(data.members);
  }
  if (data.queue) {
    renderRoomQueue(data.queue);
  }
});

socket.on("queue_updated", function(data) {
  if (data && data.room_id && currentRoom && data.room_id !== currentRoom) return;
  if (data && data.queue) {
    renderRoomQueue(data.queue);
  }
});

socket.on("room_members", function(data) {
  if (data && data.room_id && currentRoom && data.room_id !== currentRoom) return;
  if (data && data.members) {
    renderRoomMembers(data.members);
  }
});

socket.on("video_changed", function(data) {
  if (data.room_id && currentRoom && data.room_id !== currentRoom) return;
  renderPlayer(data);
  showToast(`Включено: ${data.title || 'Видео'}`);
});

socket.on("video_play", function(data) {
  if (data.room_id && currentRoom && data.room_id !== currentRoom) return;
  if (data.server_time) handleServerTimeSample(data.server_time);
  
  // If this play event was initiated by us, do not command player again
  if (data.source_sid && data.source_sid === socket.id) {
    currentVideo.playing = true;
    currentVideo.time = data.time;
    currentVideo.updated_at = data.server_time || serverNow();
    return;
  }

  isBuffering = false;
  currentVideo.playing = true;
  currentVideo.time = data.time;
  currentVideo.updated_at = data.server_time || serverNow();

  isApplyingRemoteEvent = true;
  if (currentType === "youtube") {
    const p = ytPlayer || window.ytPlayer;
    if (p) {
      const cur = (p.getCurrentTime) ? p.getCurrentTime() : data.time;
      if (Math.abs(cur - data.time) > 4.0 && p.seekTo) {
        try { p.seekTo(data.time, true); } catch(e) {}
      }
      if (p.playVideo) try { p.playVideo(); } catch(e) {}
    }
  } else {
    const el = document.getElementById("rave-video-el");
    if (el) {
      if (Math.abs(el.currentTime - data.time) > 5.0) {
        try { el.currentTime = data.time; } catch(e) {}
      }
      if (el.paused) safePlayMedia(el);
    }
  }
  updatePlayPauseUI(true);
  flashPlayPauseIcon(true);
  setTimeout(() => { isApplyingRemoteEvent = false; }, 400);
});

socket.on("video_pause", function(data) {
  if (data.room_id && currentRoom && data.room_id !== currentRoom) return;
  if (data.server_time) handleServerTimeSample(data.server_time);

  // If this pause event was initiated by us, do not command player again
  if (data.source_sid && data.source_sid === socket.id) {
    currentVideo.playing = false;
    currentVideo.time = data.time;
    currentVideo.updated_at = data.server_time || serverNow();
    return;
  }

  isBuffering = false;
  currentVideo.playing = false;
  currentVideo.time = data.time;
  currentVideo.updated_at = data.server_time || serverNow();

  isApplyingRemoteEvent = true;
  if (currentType === "youtube") {
    const p = ytPlayer || window.ytPlayer;
    if (p) {
      if (p.pauseVideo) try { p.pauseVideo(); } catch(e) {}
      const cur = (p.getCurrentTime) ? p.getCurrentTime() : data.time;
      if (Math.abs(cur - data.time) > 4.0 && p.seekTo) {
        try { p.seekTo(data.time, true); } catch(e) {}
      }
    }
  } else {
    const el = document.getElementById("rave-video-el");
    if (el) {
      if (Math.abs(el.currentTime - data.time) > 4.0) {
        try { el.currentTime = data.time; } catch(e) {}
      }
      if (!el.paused) el.pause();
    }
  }
  updatePlayPauseUI(false);
  flashPlayPauseIcon(false);
  setTimeout(() => { isApplyingRemoteEvent = false; }, 400);
});

socket.on("video_seek", function(data) {
  if (data.room_id && currentRoom && data.room_id !== currentRoom) return;
  if (data.source_sid && data.source_sid === socket.id) {
    currentVideo.time = data.time;
    currentVideo.updated_at = data.server_time || serverNow();
    return;
  }
  currentVideo.time = data.time;
  currentVideo.updated_at = data.server_time || serverNow();
  isApplyingRemoteEvent = true;
  playerSeekTo(data.time);
  onVideoTimeUpdate();
  setTimeout(() => { isApplyingRemoteEvent = false; }, 400);
});

socket.on("chat_message", appendChatMessage);
socket.on("new_message", appendChatMessage);
socket.on("receive_message", appendChatMessage);

socket.on("rooms_list", function(rooms) {
  renderPublicRooms(rooms);
});

function openRoomsModal() {
  openModal("modal-rooms-list");
  refreshRoomsModalList();
}

function refreshRoomsModalList() {
  const container = document.getElementById("rooms-list-container");
  if (container) {
    container.innerHTML = `<div style="grid-column:1/-1; text-align:center; padding:30px; color:var(--text-muted); font-size:0.85rem;">⏳ Загрузка активных комнат...</div>`;
  }
  socket.emit("get_public_rooms");
  fetch("/api/rooms")
    .then(r => r.json())
    .then(data => {
      if (data && data.rooms) {
        renderPublicRooms(data.rooms);
      }
    })
    .catch(() => {});
}

function renderPublicRooms(rooms) {
  const modalContainer = document.getElementById("rooms-list-container");
  const badgeEl = document.getElementById("rooms-modal-badge");
  const fallbackContainer = document.getElementById("public-rooms-list");

  const list = Array.isArray(rooms) ? rooms : [];
  if (badgeEl) badgeEl.textContent = list.length;

  if (modalContainer) {
    if (!list.length) {
      modalContainer.innerHTML = `
        <div style="grid-column:1/-1; text-align:center; padding:32px 16px; color:var(--text-muted); font-size:0.88rem;">
          <div style="font-size:1.6rem; margin-bottom:8px;">🚪</div>
          Нет активных комнат.<br>Нажмите «+ Новая» или создайте комнату на главной!
        </div>`;
    } else {
      modalContainer.innerHTML = "";
      list.forEach(rm => {
        const card = document.createElement("div");
        card.className = "room-modal-card";
        const vTitle = (rm.video && rm.video.title) ? rm.video.title : "Комната свободна";
        const hoursLeft = rm.hours_left || 24;
        card.innerHTML = `
          <div class="room-modal-card-header">
            <span class="room-modal-card-title">${escapeHTML(rm.name || rm.title || 'Комната')}</span>
            <span class="room-card-badge-exp" title="Комната автоматически удалится через 24 часа с момента создания">⏳ Ост. ${hoursLeft} ч</span>
          </div>
          <div class="room-card-media-title">
            <span>🎬</span>
            <span style="overflow:hidden; text-overflow:ellipsis;">${escapeHTML(vTitle)}</span>
          </div>
          <div class="room-modal-card-footer">
            <span style="font-size:0.75rem; color:var(--text-muted);">
              🟢 ${rm.online || rm.members_count || 1} в комнате
            </span>
            <button class="header-btn" style="padding:4px 12px; font-size:0.75rem; background:rgba(99,102,241,0.2); border-color:rgba(99,102,241,0.4); color:#fff;">Войти</button>
          </div>
        `;
        card.onclick = () => {
          closeModal("modal-rooms-list");
          joinRoomDirectly(rm.id);
        };
        modalContainer.appendChild(card);
      });
    }
  }

  if (fallbackContainer) {
    if (!list.length) {
      fallbackContainer.innerHTML = `<span style="grid-column:1/-1; color:var(--text-muted); font-size:0.85rem;">Нет активных комнат. Создайте свою!</span>`;
      return;
    }
    fallbackContainer.innerHTML = "";
    list.forEach(rm => {
      const card = document.createElement("div");
      card.className = "room-card";
      const vTitle = (rm.video && rm.video.title) ? rm.video.title : "Комната свободна";
      card.innerHTML = `
        <div class="room-card-title">${escapeHTML(rm.name || rm.title || 'Комната')}</div>
        <div style="font-size:0.78rem; color:var(--text-secondary); overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">🎬 ${escapeHTML(vTitle)}</div>
        <div class="room-card-meta">
          <span>👤 ${rm.online || rm.members_count || 1} в комнате</span>
          <button class="header-btn" style="padding:4px 8px; font-size:0.75rem;">Войти</button>
        </div>
      `;
      card.onclick = () => joinRoomDirectly(rm.id);
      fallbackContainer.appendChild(card);
    });
  }
}

let pingIntervalTimer = null;

async function checkHostPing(silent = false) {
  const heroTxt = document.getElementById("ping-text");
  const heroDot = document.getElementById("ping-indicator-dot");
  const headerTxt = document.getElementById("header-ping-text");
  const headerDot = document.getElementById("header-ping-dot");

  if (!silent) {
    if (heroTxt) heroTxt.textContent = "Замер...";
    if (heroDot) heroDot.className = "ping-dot measuring";
    if (headerDot) headerDot.className = "ping-dot measuring";
  }

  try {
    let avg = 0;
    if (silent) {
      // Fast single round-trip for 24/7 continuous background heartbeat
      const t0 = performance.now();
      const r = await fetch("/api/ping?_t=" + Date.now(), { cache: "no-store" });
      await r.json();
      const t1 = performance.now();
      avg = Math.max(1, Math.round(t1 - t0));
    } else {
      // 3-sample precise benchmark when clicked manually
      const latencies = [];
      for (let i = 0; i < 3; i++) {
        const t0 = performance.now();
        const r = await fetch("/api/ping?_t=" + Date.now(), { cache: "no-store" });
        await r.json();
        const t1 = performance.now();
        latencies.push(t1 - t0);
        if (i < 2) await new Promise(res => setTimeout(res, 60));
      }
      avg = Math.max(1, Math.round(latencies.reduce((a, b) => a + b, 0) / latencies.length));
    }

    let color = "#10b981"; // green
    let quality = "Отлично";
    if (avg > 150) {
      color = "#ef4444"; // red (>150ms)
      quality = "Высокий пинг";
    } else if (avg > 60) {
      color = "#f59e0b"; // yellow (60-150ms)
      quality = "Нормально";
    }

    // Update Lobby Hero Button
    if (heroTxt) {
      heroTxt.innerHTML = `Пинг: <b>${avg} ms</b>`;
    }
    if (heroDot) {
      heroDot.className = "ping-dot";
      heroDot.style.background = color;
      heroDot.style.boxShadow = `0 0 8px ${color}`;
    }

    // Update Header Pill
    if (headerTxt) {
      headerTxt.textContent = `${avg} ms`;
    }
    if (headerDot) {
      headerDot.className = "ping-dot";
      headerDot.style.background = color;
      headerDot.style.boxShadow = `0 0 8px ${color}`;
    }

    if (!silent) {
      showToast(`⚡ Пинг до сервера: ${avg} ms (${quality})`);
    }
  } catch (err) {
    if (heroTxt) heroTxt.textContent = "Офлайн";
    if (headerTxt) headerTxt.textContent = "Офлайн";
    if (heroDot) {
      heroDot.className = "ping-dot";
      heroDot.style.background = "#ef4444";
      heroDot.style.boxShadow = "none";
    }
    if (headerDot) {
      headerDot.className = "ping-dot";
      headerDot.style.background = "#ef4444";
      headerDot.style.boxShadow = "none";
    }
    if (!silent) {
      showToast("Не удалось измерить пинг до сервера");
    }
  }
}

function startContinuousPingLoop() {
  // 1. Immediate initial ping on page load
  checkHostPing(true);

  // 2. Periodic background check every 4 seconds (takes < 100 bytes)
  if (pingIntervalTimer) clearInterval(pingIntervalTimer);
  pingIntervalTimer = setInterval(() => {
    // Only query if tab is active/visible so zero battery/bandwidth is wasted when minimized
    if (!document.hidden) {
      checkHostPing(true);
    }
  }, 4000);

  // 3. Re-check immediately when tab becomes visible again
  document.addEventListener("visibilitychange", () => {
    if (!document.hidden) {
      checkHostPing(true);
    }
  });
}

function renderRoomMembers(members) {
  const listEl = document.getElementById("members-list-items");
  const bubblesEl = document.getElementById("sidebar-participants-bubbles");
  if (!members || !Array.isArray(members)) return;

  if (bubblesEl) {
    bubblesEl.innerHTML = "";
    members.forEach(m => {
      const bubble = document.createElement("div");
      bubble.className = "participant-bubble";
      bubble.innerHTML = `
        <span class="participant-dot ${m.is_buffering ? 'buffering' : ''}"></span>
        <span>${escapeHTML(m.nick || m.name || 'Участник')}</span>
      `;
      bubblesEl.appendChild(bubble);
    });
  }

  if (listEl) {
    listEl.innerHTML = "";
    members.forEach(m => {
      const row = document.createElement("div");
      row.className = "participant-item";
      row.innerHTML = `
        <div class="participant-item-left">
          <div class="header-avatar" style="width:24px; height:24px; font-size:0.68rem;">
            ${m.avatar ? `<img src="${escapeHTML(m.avatar)}">` : (m.name || 'U').charAt(0).toUpperCase()}
          </div>
          <span style="font-weight:600; font-size:0.85rem;">${escapeHTML(m.nick || m.name || 'Участник')}</span>
        </div>
        <span class="status-pill-badge ${m.is_buffering ? 'buffering' : ''}">
          ${m.is_buffering ? 'Загрузка' : 'Готов'}
        </span>
      `;
      listEl.appendChild(row);
    });
  }
}

// ==========================================================================
// 13. UTILITIES
// ==========================================================================
function openModal(id) {
  const m = document.getElementById(id);
  if (m) m.classList.add("active");
}

function closeModal(id) {
  const m = document.getElementById(id);
  if (m) m.classList.remove("active");
}

function showToast(text) {
  const t = document.getElementById("app-toast");
  if (!t) return;
  t.textContent = text;
  t.classList.add("visible");
  clearTimeout(t._timer);
  t._timer = setTimeout(() => t.classList.remove("visible"), 2500);
}

function refreshRoomsList() {
  socket.emit("get_public_rooms");
  socket.emit("rooms_list");
  showToast("Список комнат обновлен");
}

function extractYouTubeId(url) {
  if (!url) return "";
  const match = url.match(/(?:youtu\.be\/|youtube\.com\/(?:embed\/|v\/|watch\?v=|watch\?.+&v=))([\w-]{11})/);
  return match ? match[1] : "";
}

function escapeHTML(str) {
  if (!str) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function formatTimeClock(ts) {
  if (!ts) return "";
  const ms = (ts < 1e11) ? ts * 1000 : ts;
  const d = new Date(ms);
  if (isNaN(d.getTime())) return "";
  return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

// ==========================================================================
// 14. FRIENDS & DUO WATCH SYSTEM
// ==========================================================================
let lastFriendsData = [];
let friendsPollInterval = null;
window.pendingInvite = null;

function initFriendsSystem() {
  fetchFriendsActivity();
  if (friendsPollInterval) clearInterval(friendsPollInterval);
  friendsPollInterval = setInterval(fetchFriendsActivity, 6000);

  socket.on("friend_activity_update", function(data) {
    fetchFriendsActivity();
  });

  socket.on("friend_invite_received", function(data) {
    handleFriendInviteReceived(data);
  });
}

function fetchFriendsActivity() {
  fetch("/api/friends")
    .then(r => r.json())
    .then(data => {
      if (!data || !data.authenticated) {
        lastFriendsData = [];
        updateFriendsHeaderIndicator(false, 0);
        renderDuoFriendBanner(null);
        return;
      }
      const friends = data.friends || [];
      lastFriendsData = friends;

      const onlineFriends = friends.filter(f => f.is_online);
      const activeRoomFriend = friends.find(f => f.active_room);

      updateFriendsHeaderIndicator(onlineFriends.length > 0, onlineFriends.length);
      renderDuoFriendBanner(activeRoomFriend || onlineFriends[0] || null);
      renderFriendsModalList(friends);
    })
    .catch(() => {});
}

function updateFriendsHeaderIndicator(hasOnline, count) {
  const dot = document.getElementById("header-friend-dot");
  const label = document.getElementById("header-friends-label");
  if (dot) {
    if (hasOnline) {
      dot.className = "friend-online-dot online";
    } else {
      dot.className = "friend-online-dot offline";
    }
  }
  if (label) {
    if (hasOnline && lastFriendsData.length > 0) {
      const activeF = lastFriendsData.find(f => f.is_online);
      const shortName = activeF ? (activeF.display_name || activeF.username) : "Друзья";
      label.textContent = shortName;
    } else {
      label.textContent = "Друзья";
    }
  }
}

function renderDuoFriendBanner(friend) {
  const banner = document.getElementById("duo-friend-banner");
  if (!banner) return;

  // If inside room, don't show lobby banner
  if (currentRoom) {
    banner.style.display = "none";
    return;
  }

  if (!friend) {
    banner.style.display = "none";
    return;
  }

  const avatarEl = document.getElementById("duo-friend-avatar");
  const nameEl = document.getElementById("duo-friend-name");
  const badgeEl = document.getElementById("duo-status-badge");
  const titleEl = document.getElementById("duo-video-title");
  const btnTextEl = document.getElementById("duo-join-btn-text");
  const btn = document.getElementById("duo-join-btn");

  const name = friend.display_name || friend.username || "Друг";
  if (nameEl) nameEl.textContent = name;

  if (avatarEl) {
    if (friend.avatar) {
      avatarEl.innerHTML = `<img src="${escapeHTML(friend.avatar)}" alt="${escapeHTML(name)}">`;
    } else {
      avatarEl.textContent = name.charAt(0).toUpperCase();
    }
  }

  if (friend.active_room) {
    const r = friend.active_room;
    if (badgeEl) {
      badgeEl.textContent = r.playing ? "🎬 В кинозале (играет)" : "🎬 В кинозале";
      badgeEl.style.background = "rgba(168, 85, 247, 0.25)";
      badgeEl.style.color = "#d8b4fe";
      badgeEl.style.borderColor = "rgba(168, 85, 247, 0.4)";
    }
    if (titleEl) {
      const vidTitle = r.video_title && r.video_title !== "Без названия" ? r.video_title : r.title;
      titleEl.textContent = `Смотрит: «${vidTitle}»`;
    }
    if (btnTextEl) btnTextEl.textContent = `Смотреть вместе с ${name}`;
    if (btn) {
      btn.onclick = function() {
        joinDuoFriendRoom(r.room_id, r.code);
      };
    }
  } else if (friend.is_online) {
    if (badgeEl) {
      badgeEl.textContent = "🟢 Онлайн";
      badgeEl.style.background = "rgba(16, 185, 129, 0.2)";
      badgeEl.style.color = "#34d399";
      badgeEl.style.borderColor = "rgba(16, 185, 129, 0.4)";
    }
    if (titleEl) {
      titleEl.textContent = "На сайте — готов к просмотру";
    }
    if (btnTextEl) btnTextEl.textContent = `Позвать ${name}`;
    if (btn) {
      btn.onclick = function() {
        createRoomAndInviteFriend(friend.id);
      };
    }
  }

  banner.style.display = "flex";
}

function joinDuoFriendRoom(roomId, code) {
  if (!roomId) return;
  showToast("🎬 Подключение к кинозалу...");
  joinRoomDirectly(roomId, code || "");
}

function createRoomAndInviteFriend(friendId) {
  showToast("🍿 Создание комнаты и отправка приглашения...");
  const roomName = "Кинозал " + (currentUser.display_name || currentUser.username);
  socket.emit("create_room", {
    name: roomName,
    private: true,
    user: {
      id: currentUser.id,
      name: currentUser.username,
      avatar: currentUser.avatar
    }
  });

  const onCreated = function(data) {
    socket.off("room_created", onCreated);
    const rId = data.room ? data.room.id : null;
    if (rId) {
      fetch("/api/friends/invite", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ room_id: rId, friend_id: friendId })
      }).then(() => {
        showToast("✨ Приглашение успешно отправлено!");
      });
    }
  };
  socket.on("room_created", onCreated);
}

function inviteFriendFromRoom() {
  if (!currentRoom) {
    showToast("Сначала войдите в комнату");
    return;
  }
  fetch("/api/friends/invite", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ room_id: currentRoom })
  })
  .then(r => r.json())
  .then(data => {
    if (data.success) {
      showToast("✨ Приглашение отправлено!");
    } else {
      showToast(data.error || "Не удалось отправить приглашение");
    }
  })
  .catch(() => showToast("Ошибка сети"));
}

function handleFriendInviteReceived(data) {
  if (!data) return;
  if (data.target_id && currentUser && !currentUser.isGuest) {
    if (String(data.target_id) !== String(currentUser.id)) return;
  }
  if (currentRoom && String(currentRoom) === String(data.room_id)) {
    return;
  }

  window.pendingInvite = data;
  const toastEl = document.getElementById("duo-incoming-invite");
  if (!toastEl) return;

  const fromEl = document.getElementById("invite-from-name");
  const vidEl = document.getElementById("invite-video-title");
  const avEl = document.getElementById("invite-from-avatar");

  if (fromEl) fromEl.textContent = data.from_name || "Ваш друг";
  if (vidEl) vidEl.textContent = data.video_title ? `«${data.video_title}»` : "Совместный просмотр";
  if (avEl) {
    if (data.from_avatar) {
      avEl.innerHTML = `<img src="${escapeHTML(data.from_avatar)}" style="width:32px; height:32px; border-radius:50%; object-fit:cover;">`;
    } else {
      avEl.textContent = "🍿";
    }
  }

  toastEl.style.display = "flex";

  // Subtle web audio chime
  try {
    const ctx = new (window.AudioContext || window.webkitAudioContext)();
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.type = "sine";
    osc.frequency.setValueAtTime(587.33, ctx.currentTime);
    osc.frequency.setValueAtTime(880, ctx.currentTime + 0.12);
    gain.gain.setValueAtTime(0.12, ctx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.4);
    osc.connect(gain);
    gain.connect(ctx.destination);
    osc.start();
    osc.stop(ctx.currentTime + 0.4);
  } catch (e) {}

  clearTimeout(window._inviteTimer);
  window._inviteTimer = setTimeout(dismissIncomingInvite, 25000);
}

function acceptIncomingInvite() {
  if (!window.pendingInvite) return;
  const inv = window.pendingInvite;
  dismissIncomingInvite();
  joinDuoFriendRoom(inv.room_id, inv.code);
  showToast(`🍿 Смотрим вместе с ${inv.from_name}!`);
}

function dismissIncomingInvite() {
  const toastEl = document.getElementById("duo-incoming-invite");
  if (toastEl) toastEl.style.display = "none";
  window.pendingInvite = null;
  clearTimeout(window._inviteTimer);
}

function openFriendsModal() {
  openModal("modal-friends");
  fetchFriendsActivity();
}

function renderFriendsModalList(friends) {
  const container = document.getElementById("friends-list-container");
  if (!container) return;

  if (!friends || friends.length === 0) {
    container.innerHTML = `
      <div style="text-align:center; padding:24px 12px; color:var(--text-muted); font-size:0.85rem;">
        У вас пока нет друзей в списке.<br>
        Введите логин пользователя выше и нажмите «Добавить».
      </div>
    `;
    return;
  }

  container.innerHTML = friends.map(f => {
    const name = escapeHTML(f.display_name || f.username);
    const av = f.avatar
      ? `<img src="${escapeHTML(f.avatar)}" alt="${name}">`
      : name.charAt(0).toUpperCase();
    const statusText = f.is_online ? "🟢 В сети" : "⚪ Не в сети";
    const roomInfo = f.active_room
      ? `<div class="friend-card-room-badge">🎬 Смотрит: «${escapeHTML(f.active_room.video_title || f.active_room.title)}»</div>`
      : "";

    let actionBtn = "";
    if (f.active_room) {
      actionBtn = `<button class="btn-friend-join" onclick="closeModal('modal-friends'); joinDuoFriendRoom('${f.active_room.room_id}', '${f.active_room.code}')">🎬 Войти в кинозал</button>`;
    } else if (f.is_online) {
      actionBtn = `<button class="btn-friend-join" style="background:linear-gradient(135deg, #10b981, #059669);" onclick="closeModal('modal-friends'); createRoomAndInviteFriend(${f.id})">🍿 Позвать</button>`;
    }

    return `
      <div class="friend-card">
        <div class="friend-card-left">
          <div class="friend-avatar-wrap">
            <div class="friend-avatar">${av}</div>
            <span class="friend-online-dot ${f.is_online ? 'online' : 'offline'}"></span>
          </div>
          <div class="friend-card-info">
            <div class="friend-card-name">${name}</div>
            <div class="friend-card-meta">@${escapeHTML(f.username)} • ${statusText}</div>
            ${roomInfo}
          </div>
        </div>
        <div class="friend-card-right">
          ${actionBtn}
          <button class="btn-friend-remove" onclick="submitRemoveFriend(${f.id})" title="Удалить из друзей">✕</button>
        </div>
      </div>
    `;
  }).join("");
}

function submitAddFriend() {
  const input = document.getElementById("friend-add-username");
  if (!input) return;
  const username = input.value.trim();
  if (!username) {
    showToast("Введите логин пользователя");
    return;
  }
  fetch("/api/friends/add", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username: username })
  })
  .then(r => r.json())
  .then(data => {
    if (data.success) {
      input.value = "";
      showToast("✅ Пользователь добавлен в друзья!");
      fetchFriendsActivity();
    } else {
      showToast(data.error || "Не удалось добавить друга");
    }
  })
  .catch(() => showToast("Ошибка сети"));
}

function submitRemoveFriend(friendId) {
  // Optimistically remove from UI immediately
  lastFriendsData = (lastFriendsData || []).filter(f => f.id !== friendId);
  renderFriendsModalList(lastFriendsData);
  const onlineFriends = lastFriendsData.filter(f => f.is_online);
  const activeRoomFriend = lastFriendsData.find(f => f.active_room);
  updateFriendsHeaderIndicator(onlineFriends.length > 0, onlineFriends.length);
  renderDuoFriendBanner(activeRoomFriend || onlineFriends[0] || null);

  fetch("/api/friends/remove", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ friend_id: friendId })
  })
  .then(r => r.json())
  .then(data => {
    if (data.success) {
      showToast("Пользователь удалён из друзей");
      fetchFriendsActivity();
    } else {
      showToast(data.error || "Ошибка удаления");
      fetchFriendsActivity();
    }
  })
  .catch(() => {
    showToast("Ошибка сети");
    fetchFriendsActivity();
  });
}


// ==========================================================================
// 15. VIDEO QUEUE & PLAYLIST LOGIC
// ==========================================================================
let currentRoomQueue = [];

function toggleQueueModal() {
  const modal = document.getElementById("modal-queue");
  if (modal) {
    if (modal.classList.contains("active")) {
      closeModal("modal-queue");
    } else {
      openModal("modal-queue");
      renderRoomQueue(currentRoomQueue);
    }
  }
}

function renderRoomQueue(queue) {
  currentRoomQueue = Array.isArray(queue) ? queue : [];
  const badge = document.getElementById("queue-badge");
  const modalBadge = document.getElementById("queue-modal-badge");
  const list = document.getElementById("room-queue-list");

  if (badge) {
    badge.textContent = currentRoomQueue.length;
    badge.style.display = currentRoomQueue.length > 0 ? "inline-block" : "none";
  }
  if (modalBadge) {
    modalBadge.textContent = currentRoomQueue.length;
  }
  if (!list) return;

  if (currentRoomQueue.length === 0) {
    list.innerHTML = `
      <div class="queue-empty">
        <div style="font-size: 2rem; margin-bottom: 8px;">🍿</div>
        <div style="font-weight: 600; color: #fff;">Очередь воспроизведения пуста</div>
        <div style="color: var(--text-muted); font-size: 0.85rem; margin-top: 4px;">Вставьте ссылку выше, чтобы составить плейлист для совместного просмотра</div>
      </div>
    `;
    return;
  }

  list.innerHTML = currentRoomQueue.map((item, idx) => `
    <div class="queue-item" data-id="${item.id}" data-index="${idx}">
      <div class="queue-item-index">${idx + 1}</div>
      <div class="queue-item-thumb">
        ${item.poster ? `<img src="${escapeHTML(item.poster)}" alt="">` : `<div class="queue-thumb-fallback">🎬</div>`}
      </div>
      <div class="queue-item-details">
        <div class="queue-item-title" title="${escapeHTML(item.title || 'Видео')}">${escapeHTML(item.title || 'Видео')}</div>
        <div class="queue-item-meta">
          <span class="queue-item-source">${escapeHTML((item.type || 'mp4').toUpperCase())}</span>
          ${item.duration > 0 ? `<span>• ${formatMediaTime(item.duration)}</span>` : ''}
          ${item.added_by ? `<span>• от @${escapeHTML(item.added_by)}</span>` : ''}
        </div>
      </div>
      <div class="queue-item-actions">
        ${idx > 0 ? `<button class="queue-btn-action" onclick="moveQueueItem(${idx}, ${idx - 1})" title="Переместить выше">▲</button>` : `<button class="queue-btn-action disabled" disabled>▲</button>`}
        ${idx < currentRoomQueue.length - 1 ? `<button class="queue-btn-action" onclick="moveQueueItem(${idx}, ${idx + 1})" title="Переместить ниже">▼</button>` : `<button class="queue-btn-action disabled" disabled>▼</button>`}
        <button class="queue-btn-action queue-btn-play" onclick="playQueueItem('${item.id}')" title="Включить сейчас">▶</button>
        <button class="queue-btn-action queue-btn-delete" onclick="removeQueueItem('${item.id}')" title="Удалить из очереди">✕</button>
      </div>
    </div>
  `).join("");
}

function submitAddToQueue() {
  const input = document.getElementById("queue-add-url");
  if (!input) return;
  const url = input.value.trim();
  if (!url) {
    showToast("Введите ссылку на видео");
    return;
  }
  if (!currentRoom) {
    showToast("Сначала войдите в комнату");
    return;
  }
  socket.emit("queue_add", { room_id: currentRoom, url: url });
  input.value = "";
  showToast("Видео добавляется в очередь...");
}

function removeQueueItem(itemId) {
  if (!currentRoom || !itemId) return;
  socket.emit("queue_remove", { room_id: currentRoom, item_id: itemId });
}

function moveQueueItem(fromIdx, toIdx) {
  if (!currentRoom) return;
  socket.emit("queue_reorder", { room_id: currentRoom, from_index: fromIdx, to_index: toIdx });
}

function playQueueItem(itemId) {
  if (!currentRoom || !itemId) return;
  socket.emit("queue_play_item", { room_id: currentRoom, item_id: itemId });
  closeModal("modal-queue");
}

function submitPlayNextQueue() {
  if (!currentRoom) return;
  if (!currentRoomQueue || currentRoomQueue.length === 0) {
    showToast("Очередь пуста");
    return;
  }
  socket.emit("queue_play_next", { room_id: currentRoom });
  closeModal("modal-queue");
}

function submitClearQueue() {
  if (!currentRoom) return;
  if (!confirm("Очистить всю очередь видео?")) return;
  socket.emit("queue_clear", { room_id: currentRoom });
}

function onVideoEnded() {
  console.log("[Queue] Video ended event fired. isCurrentRoomLeader:", isCurrentRoomLeader, "queue length:", currentRoomQueue.length);
  if (isCurrentRoomLeader && currentRoomQueue && currentRoomQueue.length > 0) {
    showToast("🎬 Следующее видео из очереди...");
    socket.emit("queue_play_next", { room_id: currentRoom });
  }
}


// Global document listener to close player dropdown menus when clicking outside
document.addEventListener("click", function(e) {
  if (!e.target.closest(".player-speed-menu-wrap") &&
      !e.target.closest(".player-audio-menu-wrap") &&
      !e.target.closest(".player-quality-menu-wrap")) {
    closeAllDropdowns();
  }
});

