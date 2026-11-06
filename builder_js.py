# -*- coding: utf-8 -*-
"""
VD High-Performance Duo Watch JavaScript Engine
Multi-city network resilient, smooth custom player controls, and instant chat theater mode.
"""

def GET_JS():
    return r"""
// ==========================================================================
// 1. GLOBAL STATE & CONNECTION
// ==========================================================================
const socket = io({
  transports: ["websocket", "polling"],
  reconnection: true,
  reconnectionAttempts: Infinity,
  reconnectionDelay: 1000
});
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
  if (!roomView) return;

  if (collapsed) {
    roomView.classList.add("chat-collapsed");
    if (floatBtnText) floatBtnText.textContent = "Показать чат";
    if (headerBtnLabel) headerBtnLabel.textContent = "Чат (скрыт)";
    localStorage.setItem("vd_chat_collapsed", "true");
  } else {
    roomView.classList.remove("chat-collapsed");
    if (floatBtnText) floatBtnText.textContent = "Скрыть чат";
    if (headerBtnLabel) headerBtnLabel.textContent = "Чат";
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
    videoEl.addEventListener("timeupdate", onVideoTimeUpdate);
    videoEl.addEventListener("progress", onVideoBufferProgress);
    videoEl.addEventListener("loadedmetadata", onVideoLoadedMetadata);
    videoEl.addEventListener("play", () => {
      updatePlayPauseUI(true);
      flashPlayPauseIcon(true);
    });
    videoEl.addEventListener("pause", () => {
      updatePlayPauseUI(false);
      flashPlayPauseIcon(false);
      if (stage) stage.classList.remove("controls-hidden");
    });
    videoEl.addEventListener("ended", onVideoEnded);
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

  // Gesture Layer (Double clicks for -10s / +10s / Fullscreen, single click for Play/Pause)
  const zoneLeft = document.getElementById("zone-seek-left");
  const zoneRight = document.getElementById("zone-seek-right");
  const zoneCenter = document.getElementById("zone-center-play");

  if (zoneLeft) {
    zoneLeft.addEventListener("dblclick", function(e) {
      e.stopPropagation();
      seekRelative(-10);
    });
  }
  if (zoneRight) {
    zoneRight.addEventListener("dblclick", function(e) {
      e.stopPropagation();
      seekRelative(10);
    });
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
  isApplyingRemoteEvent = true;
  const isCurrentlyPlaying = (!el.paused && currentVideo && currentVideo.playing);
  if (isCurrentlyPlaying) {
    currentVideo.playing = false;
    currentVideo.time = el.currentTime;
    currentVideo.updated_at = serverNow();
    window.currentVideo = currentVideo;
    el.pause();
    updatePlayPauseIcons(false);
    if (currentRoom) socket.emit("video_pause", { room_id: currentRoom, time: el.currentTime, source_sid: socket.id });
  } else {
    currentVideo.playing = true;
    currentVideo.time = el.currentTime;
    currentVideo.updated_at = serverNow();
    window.currentVideo = currentVideo;
    safePlayMedia(el);
    updatePlayPauseIcons(true);
    if (currentRoom) socket.emit("video_play", { room_id: currentRoom, time: el.currentTime, source_sid: socket.id });
  }
  setTimeout(() => { isApplyingRemoteEvent = false; }, 500);
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

function toggleSpeedMenu() {
  const menu = document.getElementById("speed-dropdown-menu");
  if (menu) menu.classList.toggle("active");
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
  currentVideo = { type: "none", url: "", id: "", title: "", duration: 0, playing: false, time: 0, updated_at: 0 };
  currentType = "none";
  isBuffering = false;

  const emptyPlaceholder = document.getElementById("empty-player-placeholder");
  if (emptyPlaceholder) emptyPlaceholder.style.display = "flex";
  const customOverlay = document.getElementById("vd-player-overlay");
  if (customOverlay) customOverlay.style.display = "none";
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
      if (currentType === "youtube" && ytPlayer && ytPlayer.playVideo) {
        try { ytPlayer.playVideo(); } catch(e) {}
      } else if (currentType !== "youtube") {
        const el = document.getElementById("rave-video-el");
        if (el && el.paused) safePlayMedia(el);
      }
    } else {
      if (currentType === "youtube" && ytPlayer && ytPlayer.pauseVideo) {
        try { ytPlayer.pauseVideo(); } catch(e) {}
      } else if (currentType !== "youtube") {
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

  const emptyPlaceholder = document.getElementById("empty-player-placeholder");
  if (emptyPlaceholder) emptyPlaceholder.style.display = "none";

  const videoEl = document.getElementById("rave-video-el");
  const slot = document.getElementById("yt-player-slot");
  const customOverlay = document.getElementById("vd-player-overlay");

  if (currentType === "youtube") {
    // Hide HTML5 video and completely HIDE custom controls overlay so YouTube native controls have zero interference
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
  } else {
    // Hide YouTube, show native video with full custom controls
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
}

// YOUTUBE API MOUNTING
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
    onVideoEnded();
  } else if (state === YT.PlayerState.PLAYING) {
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
  if (p && typeof p.catch === 'function') {
    p.catch(err => {
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
    hlsPlayer.loadSource(video.url);
    hlsPlayer.attachMedia(videoEl);
    hlsPlayer.on(Hls.Events.MANIFEST_PARSED, function() {
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
    videoEl.src = video.url;
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
    updatePlayPauseIcons(true);
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
    updatePlayPauseIcons(false);
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
    const pUrl = "https://pixeldrain.com/api/file/" + fileId;
    startVideoDirectly({
      url: pUrl,
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
  if (currentRoom) {
    showRoomView();
    renderPlayer({
      url: payload.url,
      id: payload.id || "",
      type: payload.type || "mp4",
      title: payload.title || "Видео",
      duration: payload.duration || 0,
      playing: true,
      time: 0,
      updated_at: serverNow()
    });
    socket.emit("change_video", {
      room_id: currentRoom,
      url: payload.url,
      id: payload.id || "",
      type: payload.type || "mp4",
      title: payload.title || "Видео",
      duration: payload.duration || 0,
      playing: true
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
        url: payload.url,
        id: payload.id || "",
        type: payload.type || "mp4",
        title: payload.title || "Видео",
        duration: payload.duration || 0,
        playing: true
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
    titleEl.textContent = source === "movies" ? "Поиск фильмов" : (source === "youtube" ? "Поиск YouTube" : "Каталог видео");
  }
  if (query && input) {
    input.value = query;
    executeModalSearch();
  }
}

function executeModalSearch() {
  const input = document.getElementById("modal-search-input");
  const container = document.getElementById("modal-search-results");
  if (!input || !container) return;
  let q = input.value.trim();
  if (!q) return;

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
    input.value = "";
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
        card.style.cssText = "background:var(--bg-card); border:1px solid var(--border-color); border-radius:10px; padding:10px; cursor:pointer; display:flex; flex-direction:column; gap:8px;";
        const poster = res.poster || "/static/img/poster-fallback.jpg";
        card.innerHTML = `
          <div style="width:100%; height:130px; border-radius:6px; overflow:hidden; background:#000;">
            <img src="${escapeHTML(poster)}" style="width:100%; height:100%; object-fit:cover;" onerror="this.src='/static/img/poster-fallback.jpg'">
          </div>
          <span style="font-weight:600; font-size:0.85rem; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">${escapeHTML(res.title || 'Видео')}</span>
        `;
        card.onclick = () => {
          closeModal("modal-search-content");
          startVideoDirectly({
            url: res.url,
            type: res.type || "mp4",
            title: res.title || "Видео",
            duration: res.duration || 0
          });
        };
        container.appendChild(card);
      });
    })
    .catch(() => {
      container.innerHTML = `<span style="grid-column: 1/-1; text-align:center; padding:20px; color:#ef4444;">Ошибка поиска</span>`;
    });
}

// ==========================================================================
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

"""
