# -*- coding: utf-8 -*-
"""
VD Ultra-Minimalist High-Performance Dark Theme
Crafted with smooth spring animations, glassmorphism, responsive theater mode,
and a full-featured custom streaming player.
"""

def GET_CSS():
    return r"""
:root {
  --bg-base: #0c0c0e;
  --bg-surface: #141417;
  --bg-card: #1c1c20;
  --bg-elevated: #24242a;
  --border-color: rgba(255, 255, 255, 0.08);
  --border-hover: rgba(255, 255, 255, 0.18);
  --accent: #38bdf8;
  --accent-hover: #0ea5e9;
  --accent-gradient: linear-gradient(135deg, #06b6d4 0%, #6366f1 50%, #ec4899 100%);
  --brand-gradient: linear-gradient(135deg, #38bdf8 0%, #818cf8 50%, #c084fc 100%);
  --text-primary: #ffffff;
  --text-secondary: #a1a1aa;
  --text-muted: #71717a;
  --radius-sm: 6px;
  --radius-md: 10px;
  --radius-lg: 16px;
  --radius-pill: 9999px;
  --header-height: 56px;
  --sidebar-width: 360px;
  --font-sans: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  --font-mono: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
  --ease-spring: cubic-bezier(0.16, 1, 0.3, 1);
  --ease-smooth: cubic-bezier(0.4, 0, 0.2, 1);
}

*, *::before, *::after {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}

html, body {
  width: 100%;
  height: 100%;
  background: var(--bg-base);
  color: var(--text-primary);
  font-family: var(--font-sans);
  font-size: 14px;
  line-height: 1.5;
  overflow: hidden;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

/* Custom Sleek Scrollbars */
::-webkit-scrollbar {
  width: 6px;
  height: 6px;
}
::-webkit-scrollbar-track {
  background: transparent;
}
::-webkit-scrollbar-thumb {
  background: rgba(255, 255, 255, 0.12);
  border-radius: 999px;
}
::-webkit-scrollbar-thumb:hover {
  background: rgba(255, 255, 255, 0.24);
}

button, input, textarea, select {
  font-family: inherit;
  font-size: inherit;
  color: inherit;
  background: none;
  border: none;
  outline: none;
}

button {
  cursor: pointer;
  user-select: none;
  transition: transform 0.15s var(--ease-spring), opacity 0.15s ease, background 0.15s ease;
}
button:active {
  transform: scale(0.96) !important;
}

a {
  color: inherit;
  text-decoration: none;
}

/* APP SHELL */
.app-shell {
  display: flex;
  flex-direction: column;
  width: 100vw;
  height: 100vh;
  overflow: hidden;
  background: var(--bg-base);
}

/* TOP APP HEADER */
.app-header {
  height: var(--header-height);
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 16px;
  background: rgba(20, 20, 23, 0.85);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  border-bottom: 1px solid var(--border-color);
  z-index: 100;
  gap: 16px;
}

.header-left, .header-right {
  display: flex;
  align-items: center;
  gap: 10px;
}

.header-center {
  flex: 1;
  max-width: 680px;
  display: flex;
  justify-content: center;
}

/* BRAND MONOGRAM & TITLE */
.app-brand {
  display: flex;
  align-items: center;
  gap: 10px;
  cursor: pointer;
  padding: 4px 6px;
  border-radius: var(--radius-sm);
  transition: opacity 0.2s ease, transform 0.2s var(--ease-spring);
}
.app-brand:hover {
  opacity: 0.9;
  transform: translateY(-1px);
}
.brand-monogram {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border-radius: 9px;
  background: var(--accent-gradient);
  font-weight: 900;
  font-size: 0.95rem;
  color: #fff;
  letter-spacing: -0.5px;
  box-shadow: 0 0 16px rgba(99, 102, 241, 0.4);
  text-shadow: 0 1px 2px rgba(0,0,0,0.5);
}
.brand-title {
  font-weight: 800;
  font-size: 1.25rem;
  letter-spacing: 0.5px;
  background: var(--brand-gradient);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
}

.room-status-indicator {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #22c55e;
  box-shadow: 0 0 8px rgba(34, 197, 94, 0.6);
  animation: pulse-dot 2s infinite;
}
@keyframes pulse-dot {
  0% { transform: scale(1); opacity: 0.8; }
  50% { transform: scale(1.25); opacity: 1; }
  100% { transform: scale(1); opacity: 0.8; }
}

/* UNIVERSAL SEARCH BAR */
.universal-search-bar {
  display: flex;
  align-items: center;
  width: 100%;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-pill);
  padding: 4px 6px 4px 14px;
  gap: 8px;
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
}
.universal-search-bar:focus-within {
  border-color: rgba(56, 189, 248, 0.5);
  box-shadow: 0 0 0 3px rgba(56, 189, 248, 0.15);
}
.search-icon {
  color: var(--text-muted);
  flex-shrink: 0;
}
.universal-search-bar input {
  flex: 1;
  color: #fff;
  font-size: 0.88rem;
}
.universal-search-bar input::placeholder {
  color: var(--text-muted);
}
.search-submit-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 30px;
  height: 30px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.08);
  color: #fff;
  transition: background 0.15s ease, transform 0.15s var(--ease-spring);
}
.search-submit-btn:hover {
  background: var(--accent);
  color: #000;
  transform: scale(1.05);
}

/* HEADER ACTION BUTTONS */
.header-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  border-radius: var(--radius-pill);
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid var(--border-color);
  color: var(--text-secondary);
  font-size: 0.82rem;
  font-weight: 500;
  transition: all 0.2s var(--ease-spring);
}
.header-btn:hover {
  background: rgba(255, 255, 255, 0.12);
  color: #fff;
  border-color: var(--border-hover);
  transform: translateY(-1px);
}
.header-btn.active {
  background: var(--accent);
  color: #000;
  border-color: var(--accent);
}

/* USER PROFILE BUTTON */
.user-header-profile {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 10px 4px 4px;
  border-radius: var(--radius-pill);
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid var(--border-color);
  cursor: pointer;
  transition: all 0.2s var(--ease-spring);
}
.user-header-profile:hover {
  background: rgba(255, 255, 255, 0.1);
  border-color: var(--border-hover);
  transform: translateY(-1px);
}
.header-avatar {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: linear-gradient(135deg, #6366f1 0%, #ec4899 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: 0.75rem;
  color: #fff;
  overflow: hidden;
}
.header-avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.header-username {
  font-size: 0.85rem;
  font-weight: 600;
  color: #fff;
}

/* WORKSPACE CONTAINER */
.app-workspace {
  flex: 1;
  width: 100vw;
  height: calc(100vh - var(--header-height));
  position: relative;
  overflow: hidden;
}

.view-pane {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  display: none !important;
}
.view-pane.active {
  display: flex !important;
}

/* ========================================================================== */
/* VIEW 1: LOBBY                                                              */
/* ========================================================================== */
.lobby-view {
  flex-direction: column;
  overflow-y: auto;
  align-items: center;
  justify-content: center;
  padding: 30px 20px;
  background: radial-gradient(circle at 50% 45%, rgba(56, 189, 248, 0.08) 0%, transparent 65%);
  min-height: 100%;
}

.lobby-hero {
  max-width: 820px;
  width: 100%;
  text-align: center;
  margin-top: 0;
  margin-bottom: 32px;
  animation: heroFadeIn 0.5s var(--ease-spring);
}
@keyframes heroFadeIn {
  from { opacity: 0; transform: translateY(12px); }
  to { opacity: 1; transform: translateY(0); }
}

.lobby-badge {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 12px;
  border-radius: var(--radius-pill);
  background: rgba(56, 189, 248, 0.1);
  border: 1px solid rgba(56, 189, 248, 0.25);
  color: #38bdf8;
  font-size: 0.78rem;
  font-weight: 600;
  margin-bottom: 16px;
  letter-spacing: 0.3px;
}
.lobby-hero-title {
  font-size: 2.6rem;
  font-weight: 800;
  line-height: 1.18;
  letter-spacing: -0.5px;
  color: #fff;
  margin-bottom: 12px;
}
.lobby-hero-sub {
  font-size: 1.05rem;
  color: var(--text-secondary);
  margin-bottom: 24px;
}
.lobby-hero-actions {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  flex-wrap: wrap;
}
.btn-hero-create {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  padding: 12px 26px;
  border-radius: var(--radius-pill);
  background: var(--brand-gradient);
  color: #fff;
  font-size: 0.95rem;
  font-weight: 700;
  box-shadow: 0 4px 24px rgba(99, 102, 241, 0.4);
  transition: transform 0.2s var(--ease-spring), box-shadow 0.2s ease;
  cursor: pointer;
}
.btn-hero-create:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 30px rgba(99, 102, 241, 0.6);
}
.btn-hero-secondary {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 12px 22px;
  border-radius: var(--radius-pill);
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid var(--border-color);
  color: #fff;
  font-size: 0.95rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s var(--ease-spring);
}
.btn-hero-secondary:hover {
  background: rgba(255, 255, 255, 0.12);
  border-color: rgba(255, 255, 255, 0.25);
  transform: translateY(-2px);
  box-shadow: 0 4px 18px rgba(0, 0, 0, 0.3);
}
.header-ping-pill {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  padding: 6px 12px;
  border-radius: var(--radius-pill);
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  color: var(--text-secondary);
  font-size: 0.82rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s var(--ease-spring);
}
.header-ping-pill:hover {
  background: rgba(255, 255, 255, 0.1);
  color: var(--text-primary);
  border-color: rgba(255, 255, 255, 0.2);
}

.btn-hero-ping {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 12px 20px;
  border-radius: var(--radius-pill);
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.12);
  color: var(--text-primary);
  font-size: 0.92rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s var(--ease-spring);
}
.btn-hero-ping:hover {
  background: rgba(255, 255, 255, 0.09);
  border-color: rgba(255, 255, 255, 0.25);
  transform: translateY(-2px);
  box-shadow: 0 4px 18px rgba(0, 0, 0, 0.3);
}
.ping-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #10b981;
  box-shadow: 0 0 8px rgba(16, 185, 129, 0.8);
  display: inline-block;
  transition: background 0.3s;
}
.ping-dot.measuring {
  animation: pingPulse 0.8s infinite alternate ease-in-out;
}
@keyframes pingPulse {
  0% { transform: scale(0.8); opacity: 0.4; }
  100% { transform: scale(1.3); opacity: 1; }
}

/* 5 SOURCE CARDS */
.source-cards-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: 14px;
  max-width: 820px;
  width: 100%;
  margin-bottom: 0;
}
.source-card {
  background: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  padding: 20px 14px;
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  gap: 10px;
  cursor: pointer;
  transition: all 0.25s var(--ease-spring);
}
.source-card:hover {
  background: var(--bg-card);
  border-color: rgba(255, 255, 255, 0.2);
  transform: translateY(-4px);
  box-shadow: 0 8px 24px rgba(0,0,0,0.4);
}
.source-card-icon {
  width: 44px;
  height: 44px;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.04);
  display: flex;
  align-items: center;
  justify-content: center;
  transition: transform 0.2s var(--ease-spring);
}
.source-card:hover .source-card-icon {
  transform: scale(1.1);
}
.source-card-title {
  font-weight: 700;
  font-size: 0.88rem;
  color: #fff;
  letter-spacing: 0.3px;
}
.source-card-desc {
  font-size: 0.74rem;
  color: var(--text-muted);
  line-height: 1.35;
}

/* PUBLIC ROOMS IN LOBBY */
.lobby-section-wrap {
  max-width: 820px;
  width: 100%;
  margin-top: 10px;
}
.lobby-section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 14px;
}
.lobby-section-title {
  font-size: 1.05rem;
  font-weight: 700;
  color: #fff;
}
.public-rooms-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 12px;
}
.room-card {
  background: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  padding: 14px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  cursor: pointer;
  transition: all 0.2s var(--ease-spring);
}
.room-card:hover {
  background: var(--bg-card);
  border-color: var(--border-hover);
  transform: translateY(-2px);
}
.room-card-title {
  font-weight: 600;
  font-size: 0.92rem;
  color: #fff;
}
.room-card-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 0.78rem;
  color: var(--text-muted);
}

/* ========================================================================== */
/* VIEW 2: WATCH ROOM                                                         */
/* ========================================================================== */
.room-layout {
  display: flex;
  width: 100vw;
  height: 100%;
  background: #000;
  overflow: hidden;
  position: relative;
}

/* PLAYER STAGE CONTAINER */
.player-stage-wrap {
  flex: 1 1 auto;
  min-width: 0;
  height: 100%;
  position: relative;
  background: #000;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: width 0.35s var(--ease-spring);
}

.player-inner-container {
  width: 100%;
  height: 100%;
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #000;
  overflow: hidden;
}

/* NATIVE VIDEO & YOUTUBE SLOT */
#rave-video-el,
#yt-player-slot,
#yt-player-slot iframe,
#yt-player-target {
  width: 100% !important;
  height: 100% !important;
  position: absolute;
  inset: 0;
  object-fit: contain;
  border: none;
}

/* ========================================================================== */
/* FULL CUSTOM VD PLAYER CONTROLS OVERLAY                                     */
/* ========================================================================== */
.vd-player-overlay {
  position: absolute;
  inset: 0;
  pointer-events: none;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  z-index: 35;
  opacity: 1;
  transition: opacity 0.28s var(--ease-spring), transform 0.28s var(--ease-spring);
}

/* Auto-hide controls when idle */
.player-stage-wrap.controls-hidden .vd-player-overlay {
  opacity: 0;
  pointer-events: none !important;
}
.player-stage-wrap.controls-hidden {
  cursor: none;
}

.player-title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 2px;
}
.player-title-text {
  font-size: 0.92rem;
  font-weight: 600;
  color: #fff;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  text-shadow: 0 1px 3px rgba(0,0,0,0.8);
}

/* GESTURE & CLICK LAYER */
.player-gesture-layer {
  flex: 1;
  display: flex;
  pointer-events: auto;
  position: relative;
}

.gesture-seek-zone {
  width: 30%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  cursor: pointer;
}
.gesture-center-zone {
  flex: 1;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
}

/* Double-click seek badge animations */
.seek-ripple-badge {
  position: absolute;
  background: rgba(0, 0, 0, 0.75);
  backdrop-filter: blur(8px);
  border: 1px solid rgba(255, 255, 255, 0.15);
  border-radius: var(--radius-pill);
  padding: 8px 18px;
  font-size: 0.9rem;
  font-weight: 700;
  color: #fff;
  opacity: 0;
  pointer-events: none;
  transform: scale(0.8);
  transition: opacity 0.25s ease, transform 0.25s var(--ease-spring);
}
.seek-ripple-badge.active {
  opacity: 1;
  transform: scale(1.1);
}

/* Center Play/Pause Flash Ripple */
.center-play-flash {
  width: 72px;
  height: 72px;
  border-radius: 50%;
  background: rgba(0, 0, 0, 0.65);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(255, 255, 255, 0.15);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  opacity: 0;
  transform: scale(0.65);
  pointer-events: none;
  transition: opacity 0.3s ease, transform 0.3s var(--ease-spring);
  box-shadow: 0 8px 32px rgba(0,0,0,0.6);
}
.center-play-flash.flash {
  opacity: 1;
  transform: scale(1.05);
}
.center-play-flash svg {
  width: 32px;
  height: 32px;
}

/* BOTTOM CONTROL BAR */
.player-bottom-bar {
  padding: 30px 20px 14px;
  background: linear-gradient(to top, rgba(0, 0, 0, 0.88) 0%, rgba(0, 0, 0, 0.5) 65%, transparent 100%);
  display: flex;
  flex-direction: column;
  gap: 8px;
  pointer-events: auto;
  transition: transform 0.28s var(--ease-spring);
}
.player-stage-wrap.controls-hidden .player-bottom-bar {
  transform: translateY(10px);
}

/* TIMELINE SCRUBBER */
.player-timeline-container {
  width: 100%;
  height: 18px;
  display: flex;
  align-items: center;
  cursor: pointer;
  position: relative;
  user-select: none;
}

.timeline-hover-tooltip {
  position: absolute;
  top: -28px;
  left: 0;
  transform: translateX(-50%);
  background: rgba(24, 24, 27, 0.95);
  backdrop-filter: blur(6px);
  border: 1px solid rgba(255, 255, 255, 0.15);
  color: #fff;
  padding: 2px 7px;
  border-radius: var(--radius-sm);
  font-size: 0.72rem;
  font-family: var(--font-mono);
  font-weight: 600;
  pointer-events: none;
  opacity: 0;
  transition: opacity 0.15s ease;
  white-space: nowrap;
}
.player-timeline-container:hover .timeline-hover-tooltip {
  opacity: 1;
}

.timeline-track {
  width: 100%;
  height: 4px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.2);
  position: relative;
  transition: height 0.18s var(--ease-spring);
}
.player-timeline-container:hover .timeline-track,
.player-timeline-container.scrubbing .timeline-track {
  height: 6px;
}

.timeline-buffer {
  position: absolute;
  left: 0;
  top: 0;
  height: 100%;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.35);
  width: 0%;
  transition: width 0.2s ease;
}

.timeline-progress {
  position: absolute;
  left: 0;
  top: 0;
  height: 100%;
  border-radius: 999px;
  background: linear-gradient(90deg, #38bdf8 0%, #818cf8 100%);
  width: 0%;
  position: relative;
}

.timeline-thumb {
  position: absolute;
  right: -6px;
  top: 50%;
  transform: translateY(-50%) scale(0);
  width: 14px;
  height: 14px;
  border-radius: 50%;
  background: #fff;
  box-shadow: 0 0 10px rgba(56, 189, 248, 0.8);
  transition: transform 0.18s var(--ease-spring);
}
.player-timeline-container:hover .timeline-thumb,
.player-timeline-container.scrubbing .timeline-thumb {
  transform: translateY(-50%) scale(1);
}

/* CONTROLS ROW */
.player-controls-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
}

.controls-left, .controls-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.player-ctrl-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border-radius: 50%;
  color: #fff;
  background: transparent;
  transition: background 0.15s ease, transform 0.15s var(--ease-spring);
}
.player-ctrl-btn:hover {
  background: rgba(255, 255, 255, 0.12);
  transform: scale(1.08);
}
.player-ctrl-btn svg {
  width: 20px;
  height: 20px;
}

/* VOLUME GROUP */
.player-volume-group {
  display: flex;
  align-items: center;
  position: relative;
}
.player-volume-slider-wrap {
  width: 0;
  overflow: hidden;
  transition: width 0.25s var(--ease-spring);
  display: flex;
  align-items: center;
}
.player-volume-group:hover .player-volume-slider-wrap,
.player-volume-group:focus-within .player-volume-slider-wrap {
  width: 72px;
  margin-right: 6px;
}
.player-volume-slider-wrap input[type="range"] {
  width: 68px;
  height: 4px;
  accent-color: var(--accent);
  cursor: pointer;
}

/* TIME DISPLAY */
.player-time-display {
  display: flex;
  align-items: center;
  gap: 4px;
  font-family: var(--font-mono);
  font-size: 0.8rem;
  color: #e4e4e7;
  padding: 4px 6px;
  border-radius: var(--radius-sm);
  cursor: pointer;
  user-select: none;
  transition: color 0.15s ease;
}
.player-time-display:hover {
  color: #fff;
}
.time-sep {
  color: var(--text-muted);
}

/* CATCHUP PILL */
.player-catchup-pill {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  background: rgba(239, 68, 68, 0.85);
  backdrop-filter: blur(8px);
  color: #fff;
  padding: 4px 10px;
  border-radius: var(--radius-pill);
  font-size: 0.74rem;
  font-weight: 700;
  cursor: pointer;
  animation: pulse-warn 1.5s infinite;
  box-shadow: 0 2px 10px rgba(239, 68, 68, 0.4);
}
@keyframes pulse-warn {
  0% { transform: scale(1); }
  50% { transform: scale(1.04); }
  100% { transform: scale(1); }
}

/* PLAYBACK SPEED DROPDOWN */
.player-speed-menu-wrap {
  position: relative;
}
.player-speed-btn {
  font-weight: 700;
  font-size: 0.82rem;
  border-radius: var(--radius-sm);
  width: auto;
  padding: 4px 8px;
}
.speed-dropdown-menu {
  position: absolute;
  bottom: 44px;
  right: 0;
  background: rgba(20, 20, 23, 0.95);
  backdrop-filter: blur(12px);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  padding: 6px;
  display: none;
  flex-direction: column;
  gap: 2px;
  box-shadow: 0 8px 24px rgba(0,0,0,0.5);
  z-index: 50;
  min-width: 120px;
}
.speed-dropdown-menu.active {
  display: flex;
}

/* ========================================================================== */
/* AUDIO DUBBING TRACK SELECTOR MENU                                         */
/* ========================================================================== */
.player-audio-menu-wrap {
  position: relative;
  display: inline-flex;
  align-items: center;
}
.audio-dropdown-menu {
  position: absolute;
  bottom: 44px;
  right: 0;
  background: rgba(20, 20, 23, 0.95);
  backdrop-filter: blur(14px);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  padding: 6px;
  display: none;
  flex-direction: column;
  gap: 3px;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.7);
  z-index: 60;
  min-width: 170px;
  max-width: 260px;
  max-height: 240px;
  overflow-y: auto;
}
.audio-dropdown-menu.active {
  display: flex;
}
.audio-opt {
  padding: 7px 12px;
  border-radius: var(--radius-sm);
  font-size: 0.82rem;
  font-weight: 500;
  color: var(--text-secondary);
  cursor: pointer;
  transition: all 0.15s ease;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  display: flex;
  align-items: center;
  gap: 6px;
}
.audio-opt:hover {
  background: rgba(255, 255, 255, 0.08);
  color: var(--text-primary);
}
.audio-opt.active {
  background: rgba(139, 92, 246, 0.22);
  color: #c084fc;
  font-weight: 600;
}

/* ========================================================================== */
/* FLOATING EMOJI REACTION SYSTEM                                             */
/* ========================================================================== */
.reaction-layer {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
  overflow: hidden;
  z-index: 45;
}
.floating-emoji {
  position: absolute;
  bottom: 50px;
  font-size: 2.3rem;
  line-height: 1;
  pointer-events: none;
  user-select: none;
  animation: floatEmojiUp 2.2s cubic-bezier(0.18, 0.89, 0.32, 1.15) forwards;
  filter: drop-shadow(0 6px 14px rgba(0, 0, 0, 0.7));
}
@keyframes floatEmojiUp {
  0% {
    opacity: 0;
    transform: translateY(20px) scale(0.5) rotate(0deg);
  }
  12% {
    opacity: 1;
    transform: translateY(0) scale(1.25) rotate(var(--rot-deg, -8deg));
  }
  55% {
    opacity: 0.95;
    transform: translateY(-130px) scale(1.35) rotate(var(--rot-deg-mid, 8deg));
  }
  100% {
    opacity: 0;
    transform: translateY(-290px) scale(1.65) rotate(var(--rot-deg-end, 18deg));
  }
}
.chat-reactions-row {
  display: flex;
  gap: 6px;
  padding: 6px 10px 4px 10px;
  align-items: center;
  justify-content: space-around;
  background: transparent;
  border-top: 1px solid rgba(255, 255, 255, 0.05);
}
.reaction-btn {
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 14px;
  padding: 4px 9px;
  font-size: 1.2rem;
  cursor: pointer;
  line-height: 1;
  transition: transform 0.18s cubic-bezier(0.34, 1.56, 0.64, 1), background 0.15s;
}
.reaction-btn:hover {
  transform: scale(1.35);
  background: rgba(255, 255, 255, 0.16);
}
.reaction-btn:active {
  transform: scale(0.9);
}
.speed-opt {
  padding: 6px 10px;
  border-radius: var(--radius-sm);
  font-size: 0.8rem;
  font-weight: 500;
  color: var(--text-secondary);
  cursor: pointer;
  transition: all 0.15s ease;
}
.speed-opt:hover {
  background: rgba(255, 255, 255, 0.08);
  color: #fff;
}
.speed-opt.active {
  background: var(--accent);
  color: #000;
  font-weight: 700;
}

/* EMPTY ROOM PLACEHOLDER */
.empty-player-placeholder {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  padding: 24px;
  background: #0d0d0f;
  z-index: 5;
}
.empty-icon-cloud {
  margin-bottom: 16px;
}
.empty-title {
  font-size: 1.35rem;
  font-weight: 700;
  color: #fff;
  margin-bottom: 8px;
}
.empty-sub {
  font-size: 0.88rem;
  color: var(--text-muted);
  max-width: 440px;
  margin-bottom: 24px;
}
.empty-actions-row {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  justify-content: center;
}

/* DRAG & DROP OVERLAY */
.player-drop-overlay {
  position: absolute;
  inset: 0;
  background: rgba(14, 165, 233, 0.88);
  backdrop-filter: blur(6px);
  display: none;
  align-items: center;
  justify-content: center;
  z-index: 50;
  flex-direction: column;
  gap: 12px;
  color: #fff;
}
.player-drop-overlay.active {
  display: flex;
}

/* ========================================================================== */
/* COLLAPSIBLE RIGHT SIDEBAR (CHAT & PARTICIPANTS)                            */
/* ========================================================================== */
.room-sidebar {
  width: var(--sidebar-width);
  min-width: 0;
  max-width: var(--sidebar-width);
  flex-shrink: 0;
  height: 100%;
  background: var(--bg-surface);
  border-left: 1px solid var(--border-color);
  display: flex;
  flex-direction: column;
  transition: width 0.35s var(--ease-spring), max-width 0.35s var(--ease-spring), opacity 0.25s ease;
  overflow: hidden;
  z-index: 30;
}

/* COLLAPSED THEATER MODE */
.room-layout.chat-collapsed .room-sidebar {
  width: 0 !important;
  min-width: 0 !important;
  max-width: 0 !important;
  opacity: 0 !important;
  pointer-events: none !important;
  border: none !important;
  border-left: none !important;
}

.room-layout.chat-collapsed .player-stage-wrap {
  width: 100vw !important;
  max-width: 100vw !important;
}

/* SIDEBAR HEADER & TABS */
.sidebar-header {
  padding: 12px 14px 8px;
  border-bottom: 1px solid var(--border-color);
  display: flex;
  flex-direction: column;
  gap: 10px;
  flex-shrink: 0;
}
.sidebar-participants-row {
  display: flex;
  align-items: center;
  gap: 8px;
  overflow-x: auto;
  padding-bottom: 4px;
}
.participant-bubble {
  position: relative;
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 3px 8px 3px 4px;
  border-radius: var(--radius-pill);
  background: rgba(255, 255, 255, 0.05);
  font-size: 0.75rem;
  font-weight: 500;
  color: #fff;
  flex-shrink: 0;
}
.participant-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #22c55e;
}
.participant-dot.buffering {
  background: #eab308;
  animation: pulse-dot 1s infinite;
}

.sidebar-tabs {
  display: flex;
  gap: 4px;
  background: rgba(0, 0, 0, 0.25);
  padding: 3px;
  border-radius: var(--radius-pill);
}
.sidebar-tab-btn {
  flex: 1;
  text-align: center;
  padding: 6px 10px;
  border-radius: var(--radius-pill);
  font-size: 0.8rem;
  font-weight: 600;
  color: var(--text-secondary);
  transition: all 0.15s ease;
}
.sidebar-tab-btn:hover {
  color: #fff;
}
.sidebar-tab-btn.active {
  background: var(--bg-card);
  color: #fff;
  box-shadow: 0 1px 3px rgba(0,0,0,0.3);
}

/* SIDEBAR CONTENT PANES */
.sidebar-content-pane {
  flex: 1;
  display: none;
  flex-direction: column;
  overflow: hidden;
}
.sidebar-content-pane.active {
  display: flex;
}

/* CHAT MESSAGES */
.chat-messages-container {
  flex: 1;
  overflow-y: auto;
  padding: 14px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.chat-msg-row {
  display: flex;
  gap: 8px;
  align-items: flex-start;
  animation: chatSlideIn 0.25s var(--ease-spring);
}
@keyframes chatSlideIn {
  from { opacity: 0; transform: translateY(6px); }
  to { opacity: 1; transform: translateY(0); }
}
.chat-msg-avatar {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: linear-gradient(135deg, #4f46e5 0%, #06b6d4 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.7rem;
  font-weight: 700;
  color: #fff;
  flex-shrink: 0;
  overflow: hidden;
}
.chat-msg-avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.chat-msg-bubble {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 12px;
  padding: 8px 12px;
  max-width: 82%;
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.chat-msg-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}
.chat-msg-author {
  font-size: 0.76rem;
  font-weight: 700;
  color: #38bdf8;
}
.chat-msg-time {
  font-size: 0.68rem;
  color: var(--text-muted);
}
.chat-msg-text {
  font-size: 0.85rem;
  color: #e4e4e7;
  word-break: break-word;
}

/* CHAT INPUT BAR */
.chat-input-bar {
  padding: 10px 12px;
  border-top: 1px solid var(--border-color);
  display: flex;
  gap: 8px;
  align-items: center;
  background: var(--bg-surface);
}
.chat-input-bar input {
  flex: 1;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-pill);
  padding: 8px 14px;
  color: #fff;
  font-size: 0.85rem;
}
.chat-input-bar input:focus {
  border-color: rgba(56, 189, 248, 0.4);
}
.chat-send-btn {
  width: 34px;
  height: 34px;
  border-radius: 50%;
  background: var(--accent);
  color: #000;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  transition: background 0.15s ease, transform 0.15s var(--ease-spring);
}
.chat-send-btn:hover {
  background: var(--accent-hover);
  transform: scale(1.05);
}

/* SETTINGS / PARTICIPANTS PANE */
.settings-pane-container {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.settings-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.settings-group-title {
  font-size: 0.8rem;
  font-weight: 700;
  text-transform: uppercase;
  color: var(--text-muted);
  letter-spacing: 0.5px;
}
.participant-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 12px;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
}
.participant-item-left {
  display: flex;
  align-items: center;
  gap: 8px;
}
.status-pill-badge {
  font-size: 0.72rem;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: var(--radius-pill);
  background: rgba(34, 197, 94, 0.15);
  color: #4ade80;
}
.status-pill-badge.buffering {
  background: rgba(234, 179, 8, 0.15);
  color: #facc15;
}

/* MODALS */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.75);
  backdrop-filter: blur(8px);
  display: none;
  align-items: center;
  justify-content: center;
  z-index: 200;
  padding: 16px;
}
.modal-overlay.active {
  display: flex;
}
.modal-dialog {
  background: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  max-width: 560px;
  width: 100%;
  box-shadow: 0 10px 40px rgba(0,0,0,0.6);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  animation: modalScaleIn 0.25s var(--ease-spring);
}
@keyframes modalScaleIn {
  from { opacity: 0; transform: scale(0.96) translateY(8px); }
  to { opacity: 1; transform: scale(1) translateY(0); }
}
.modal-dialog-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  border-bottom: 1px solid var(--border-color);
}
.modal-dialog-title {
  font-size: 1.05rem;
  font-weight: 700;
  color: #fff;
}
.modal-dialog-close {
  color: var(--text-muted);
  padding: 4px;
  border-radius: 6px;
}
.modal-dialog-close:hover {
  color: #fff;
  background: rgba(255, 255, 255, 0.08);
}
.modal-dialog-body {
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  overflow-y: auto;
  max-height: 80vh;
}

.modal-dialog-rooms {
  max-width: 680px;
  width: 92%;
}
.badge-rooms-count {
  padding: 2px 8px;
  font-size: 0.75rem;
  font-weight: 700;
  border-radius: 9999px;
  background: rgba(99, 102, 241, 0.2);
  color: #818cf8;
  border: 1px solid rgba(99, 102, 241, 0.35);
}
.btn-refresh-rooms {
  background: transparent;
  border: none;
  color: var(--text-secondary);
  cursor: pointer;
  padding: 6px;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all 0.2s;
}
.btn-refresh-rooms:hover {
  color: #fff;
  background: rgba(255, 255, 255, 0.08);
}
.rooms-modal-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 12px;
  max-height: 52vh;
  overflow-y: auto;
  padding: 2px;
}
.room-modal-card {
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 12px;
  padding: 14px 16px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  transition: all 0.2s ease;
  cursor: pointer;
}
.room-modal-card:hover {
  border-color: rgba(99, 102, 241, 0.45);
  background: rgba(255, 255, 255, 0.04);
  transform: translateY(-2px);
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.3);
}
.room-modal-card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}
.room-modal-card-title {
  font-size: 0.95rem;
  font-weight: 700;
  color: #fff;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.room-card-badge-exp {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 2px 7px;
  border-radius: 4px;
  background: rgba(245, 158, 11, 0.12);
  border: 1px solid rgba(245, 158, 11, 0.3);
  color: #fbbf24;
  font-size: 0.7rem;
  font-weight: 600;
  white-space: nowrap;
}
.room-card-media-title {
  font-size: 0.8rem;
  color: var(--text-secondary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  display: flex;
  align-items: center;
  gap: 6px;
}
.room-modal-card-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 4px;
  padding-top: 8px;
  border-top: 1px solid rgba(255, 255, 255, 0.06);
}

/* TOAST NOTIFICATION */
#app-toast {
  position: fixed;
  bottom: 24px;
  left: 50%;
  transform: translateX(-50%) translateY(100px);
  background: rgba(24, 24, 27, 0.95);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(255, 255, 255, 0.15);
  color: #fff;
  padding: 10px 20px;
  border-radius: var(--radius-pill);
  font-size: 0.85rem;
  font-weight: 600;
  box-shadow: 0 8px 30px rgba(0,0,0,0.5);
  pointer-events: none;
  opacity: 0;
  transition: transform 0.25s var(--ease-spring), opacity 0.25s ease;
  z-index: 500;
}
#app-toast.visible {
  transform: translateX(-50%) translateY(0);
  opacity: 1;
}

/* ========================================================================== */
/* FRIENDS & DUO WATCH SYSTEM STYLES                                          */
/* ========================================================================== */
.friend-online-dot {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  margin-right: 2px;
  transition: background-color 0.2s ease, box-shadow 0.2s ease;
}
.friend-online-dot.online {
  background-color: #10b981;
  box-shadow: 0 0 8px rgba(16, 185, 129, 0.7);
}
.friend-online-dot.offline {
  background-color: #64748b;
  box-shadow: none;
}

/* AVATAR PRESETS */
.preset-avatar-btn {
  width: 38px;
  height: 38px;
  border-radius: 50%;
  border: 2px solid rgba(255, 255, 255, 0.15);
  cursor: pointer;
  overflow: hidden;
  flex-shrink: 0;
  transition: all 0.2s ease;
  padding: 0;
  background: #18181b;
}
.preset-avatar-btn:hover {
  transform: scale(1.15);
  border-color: var(--accent);
  box-shadow: 0 0 12px rgba(168, 85, 247, 0.6);
}
.preset-avatar-btn img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

/* DUO LIVE ACTIVITY CARD (LOBBY HERO) */
.duo-activity-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  background: linear-gradient(135deg, rgba(168, 85, 247, 0.16) 0%, rgba(99, 102, 241, 0.12) 100%);
  border: 1px solid rgba(168, 85, 247, 0.4);
  backdrop-filter: blur(12px);
  border-radius: 16px;
  padding: 14px 20px;
  margin: 18px auto 0 auto;
  max-width: 680px;
  box-shadow: 0 8px 32px rgba(168, 85, 247, 0.18), 0 0 1px rgba(255, 255, 255, 0.2) inset;
  transition: all 0.25s ease;
  animation: fadeInScale 0.3s ease;
}
.duo-activity-card:hover {
  border-color: rgba(168, 85, 247, 0.6);
  box-shadow: 0 12px 36px rgba(168, 85, 247, 0.28);
}
@keyframes fadeInScale {
  from { opacity: 0; transform: translateY(-8px) scale(0.98); }
  to { opacity: 1; transform: translateY(0) scale(1); }
}
.duo-card-left {
  display: flex;
  align-items: center;
  gap: 14px;
  min-width: 0;
}
.duo-avatar-wrap {
  position: relative;
  flex-shrink: 0;
}
.duo-avatar {
  width: 44px;
  height: 44px;
  border-radius: 50%;
  background: linear-gradient(135deg, #a855f7, #6366f1);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: 1.1rem;
  overflow: hidden;
  border: 2px solid rgba(255, 255, 255, 0.15);
}
.duo-avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.duo-status-pulse {
  position: absolute;
  bottom: 0;
  right: 0;
  width: 12px;
  height: 12px;
  background-color: #10b981;
  border-radius: 50%;
  border: 2px solid #0f0f13;
  box-shadow: 0 0 8px #10b981;
  animation: duoPulse 2s infinite;
}
@keyframes duoPulse {
  0% { box-shadow: 0 0 0 0 rgba(16, 185, 129, 0.7); }
  70% { box-shadow: 0 0 0 8px rgba(16, 185, 129, 0); }
  100% { box-shadow: 0 0 0 0 rgba(16, 185, 129, 0); }
}
.duo-info {
  display: flex;
  flex-direction: column;
  gap: 3px;
  min-width: 0;
  text-align: left;
}
.duo-name-row {
  display: flex;
  align-items: center;
  gap: 8px;
}
.duo-friend-name {
  font-weight: 700;
  font-size: 1rem;
  color: #fff;
  white-space: nowrap;
}
.duo-badge {
  font-size: 0.7rem;
  font-weight: 700;
  padding: 2px 8px;
  border-radius: 999px;
  background: rgba(168, 85, 247, 0.25);
  color: #d8b4fe;
  border: 1px solid rgba(168, 85, 247, 0.4);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}
.duo-video-title {
  font-size: 0.85rem;
  color: rgba(255, 255, 255, 0.85);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 320px;
}
.btn-duo-join {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  background: linear-gradient(135deg, #a855f7 0%, #7c3aed 100%);
  color: #fff;
  border: none;
  border-radius: 12px;
  padding: 10px 18px;
  font-size: 0.9rem;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.2s ease;
  box-shadow: 0 4px 18px rgba(168, 85, 247, 0.4);
  white-space: nowrap;
}
.btn-duo-join:hover {
  transform: scale(1.03);
  box-shadow: 0 6px 24px rgba(168, 85, 247, 0.6);
}

/* LIVE INCOMING DUO INVITATION TOAST */
.duo-incoming-invite {
  position: fixed;
  top: 24px;
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18px;
  background: rgba(20, 20, 26, 0.96);
  backdrop-filter: blur(16px);
  border: 1.5px solid rgba(168, 85, 247, 0.55);
  box-shadow: 0 16px 48px rgba(0, 0, 0, 0.7), 0 0 24px rgba(168, 85, 247, 0.35);
  border-radius: 16px;
  padding: 14px 20px;
  z-index: 1000;
  max-width: 90vw;
  width: 520px;
  animation: slideDownInvite 0.35s cubic-bezier(0.16, 1, 0.3, 1);
}
@keyframes slideDownInvite {
  from { opacity: 0; transform: translate(-50%, -40px); }
  to { opacity: 1; transform: translate(-50%, 0); }
}
.invite-content {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 0;
}
.invite-avatar {
  font-size: 1.6rem;
  flex-shrink: 0;
}
.invite-texts {
  min-width: 0;
  text-align: left;
}
.invite-title {
  font-size: 0.85rem;
  color: rgba(255, 255, 255, 0.9);
}
.invite-video {
  font-size: 0.95rem;
  font-weight: 700;
  color: #c084fc;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.invite-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}
.invite-btn-accept {
  background: linear-gradient(135deg, #10b981 0%, #059669 100%);
  color: #fff;
  border: none;
  border-radius: 10px;
  padding: 8px 14px;
  font-size: 0.82rem;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.15s ease;
  box-shadow: 0 4px 12px rgba(16, 185, 129, 0.4);
  white-space: nowrap;
}
.invite-btn-accept:hover {
  transform: scale(1.04);
}
.invite-btn-decline {
  background: rgba(255, 255, 255, 0.08);
  color: var(--text-muted);
  border: 1px solid var(--border-color);
  border-radius: 10px;
  padding: 8px 12px;
  font-size: 0.85rem;
  cursor: pointer;
}
.invite-btn-decline:hover {
  color: #fff;
  background: rgba(255, 255, 255, 0.15);
}

/* FRIENDS MODAL & LIST */
.modal-dialog-friends {
  max-width: 540px;
}
.friends-add-bar {
  display: flex;
  gap: 8px;
  margin-bottom: 16px;
}
.friends-add-bar input {
  flex: 1;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  padding: 9px 14px;
  color: #fff;
  font-size: 0.88rem;
}
.friends-list-grid {
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-height: 340px;
  overflow-y: auto;
}
.friend-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  background: var(--bg-card);
  border: 1px solid var(--border-color);
  border-radius: 12px;
  padding: 12px 14px;
  transition: all 0.2s ease;
}
.friend-card:hover {
  border-color: rgba(255, 255, 255, 0.15);
  background: rgba(255, 255, 255, 0.04);
}
.friend-card-left {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 0;
}
.friend-avatar-wrap {
  position: relative;
  flex-shrink: 0;
}
.friend-avatar {
  width: 38px;
  height: 38px;
  border-radius: 50%;
  background: #27272a;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  color: #fff;
  overflow: hidden;
}
.friend-avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.friend-card-info {
  min-width: 0;
  text-align: left;
}
.friend-card-name {
  font-weight: 700;
  font-size: 0.92rem;
  color: #fff;
  white-space: nowrap;
}
.friend-card-meta {
  font-size: 0.75rem;
  color: var(--text-muted);
  white-space: nowrap;
}
.friend-card-room-badge {
  margin-top: 3px;
  font-size: 0.72rem;
  color: #c084fc;
  font-weight: 600;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.friend-card-right {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}
.btn-friend-join {
  background: linear-gradient(135deg, #a855f7, #6366f1);
  color: #fff;
  border: none;
  border-radius: 8px;
  padding: 6px 12px;
  font-size: 0.78rem;
  font-weight: 700;
  cursor: pointer;
  transition: transform 0.15s ease;
  white-space: nowrap;
}
.btn-friend-join:hover {
  transform: scale(1.04);
}
.btn-friend-remove {
  background: transparent;
  border: none;
  color: var(--text-muted);
  font-size: 0.85rem;
  cursor: pointer;
  padding: 6px;
  border-radius: 6px;
}
.btn-friend-remove:hover {
  color: #ef4444;
  background: rgba(239, 68, 68, 0.1);
}
.friends-hint-box {
  margin-top: 14px;
  padding: 10px 14px;
  background: rgba(168, 85, 247, 0.08);
  border: 1px solid rgba(168, 85, 247, 0.2);
  border-radius: 10px;
  font-size: 0.78rem;
  line-height: 1.45;
  color: rgba(255, 255, 255, 0.75);
}

/* ========================================================================== */
/* VIDEO QUEUE & PLAYLIST STYLES                                              */
/* ========================================================================== */
.modal-dialog-queue {
  max-width: 620px;
  width: 95%;
  max-height: 85vh;
  display: flex;
  flex-direction: column;
}
.queue-add-box {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
}
.queue-add-box input {
  flex: 1;
  background: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  padding: 10px 14px;
  color: var(--text-primary);
  font-size: 0.88rem;
  outline: none;
  transition: border-color 0.15s ease;
}
.queue-add-box input:focus {
  border-color: var(--accent);
}
.queue-actions-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 12px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid var(--border-color);
  border-radius: 8px;
  margin-bottom: 14px;
  font-size: 0.8rem;
}
.queue-status-hint {
  color: var(--text-secondary);
}
.queue-action-pill {
  background: rgba(255, 255, 255, 0.08);
  border: 1px solid var(--border-color);
  color: var(--text-primary);
  border-radius: 6px;
  padding: 5px 12px;
  font-size: 0.76rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s ease;
}
.queue-action-pill:hover {
  background: rgba(255, 255, 255, 0.15);
}
.queue-action-pill.danger:hover {
  background: rgba(239, 68, 68, 0.2);
  color: #ef4444;
  border-color: rgba(239, 68, 68, 0.4);
}
.queue-list-container {
  display: flex;
  flex-direction: column;
  gap: 8px;
  overflow-y: auto;
  max-height: 480px;
  padding-right: 4px;
}
.queue-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 8px 12px;
  background: var(--bg-surface);
  border: 1px solid var(--border-color);
  border-radius: 10px;
  transition: transform 0.15s ease, border-color 0.15s ease;
}
.queue-item:hover {
  border-color: var(--border-hover);
}
.queue-item-index {
  font-size: 0.85rem;
  font-weight: 700;
  color: var(--accent);
  width: 22px;
  text-align: center;
  flex-shrink: 0;
}
.queue-item-thumb {
  width: 60px;
  height: 38px;
  border-radius: 6px;
  overflow: hidden;
  background: #000;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.queue-item-thumb img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.queue-thumb-fallback {
  font-size: 1.1rem;
}
.queue-item-details {
  flex: 1;
  min-width: 0;
}
.queue-item-title {
  font-size: 0.86rem;
  font-weight: 600;
  color: #fff;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.queue-item-meta {
  display: flex;
  gap: 6px;
  font-size: 0.74rem;
  color: var(--text-secondary);
  margin-top: 2px;
}
.queue-item-source {
  background: rgba(56, 189, 248, 0.15);
  color: var(--accent);
  padding: 1px 5px;
  border-radius: 4px;
  font-weight: 700;
  font-size: 0.68rem;
}
.queue-item-actions {
  display: flex;
  gap: 4px;
  align-items: center;
  flex-shrink: 0;
}
.queue-btn-action {
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid var(--border-color);
  color: var(--text-secondary);
  border-radius: 6px;
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  font-size: 0.75rem;
  transition: all 0.12s ease;
}
.queue-btn-action:hover {
  background: rgba(255, 255, 255, 0.15);
  color: #fff;
}
.queue-btn-action.disabled {
  opacity: 0.3;
  cursor: not-allowed;
}
.queue-btn-play:hover {
  background: rgba(56, 189, 248, 0.2);
  color: var(--accent);
  border-color: rgba(56, 189, 248, 0.4);
}
.queue-btn-delete:hover {
  background: rgba(239, 68, 68, 0.2);
  color: #ef4444;
  border-color: rgba(239, 68, 68, 0.4);
}
.queue-empty {
  text-align: center;
  padding: 36px 16px;
  border: 1px dashed var(--border-color);
  border-radius: 12px;
  margin: 10px 0;
}

/* ========================================================================== */
/* MOBILE RESPONSIVE OPTIMIZATIONS (SMARTPHONES & TABLETS)                    */
/* ========================================================================== */
@media (max-width: 768px) {
  :root {
    --header-height: 48px;
    --sidebar-width: 100%;
  }

  /* Safe Area for iOS Notch & Dynamic Viewport Height */
  html, body {
    height: 100%;
    height: 100dvh;
    overflow-x: hidden;
  }

  .app-container {
    height: 100dvh;
  }

  /* Header on Mobile: Zero horizontal overflow */
  .app-header {
    padding: 0 6px;
    gap: 4px;
    overflow-x: hidden;
    height: var(--header-height);
  }
  .header-left {
    gap: 4px;
    flex-shrink: 0;
    display: flex;
    align-items: center;
  }
  .app-brand {
    padding: 2px 4px;
    gap: 4px;
  }
  .brand-monogram {
    width: 28px;
    height: 28px;
    font-size: 0.85rem;
  }
  .header-room-pill {
    padding: 2px 6px;
    font-size: 0.68rem;
    max-width: 75px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  /* Hide textual labels on header buttons on mobile to fit nicely */
  .header-btn .header-btn-label {
    display: none !important;
  }
  .header-btn {
    padding: 5px 6px !important;
    font-size: 0.75rem;
    min-width: 28px;
    height: 30px;
    justify-content: center;
    border-radius: 6px;
  }
  .header-right {
    gap: 3px;
    flex-shrink: 0;
    display: flex;
    align-items: center;
  }
  /* Hide non-essential ping indicator and copy link button on phone screens to give room to controls */
  .header-ping-pill, #btn-copy-room-link {
    display: none !important;
  }
  .user-header-profile {
    padding: 2px 4px;
    gap: 4px;
  }
  .header-username {
    display: none;
  }
  .header-avatar {
    width: 26px;
    height: 26px;
    font-size: 0.75rem;
  }

  /* Universal Search Bar on Mobile */
  .header-center {
    flex: 1 1 auto;
    min-width: 0;
    max-width: 100%;
    margin: 0 4px;
    display: flex;
    justify-content: center;
  }
  .universal-search-bar {
    width: 100%;
    min-width: 0;
    padding: 2px 4px 2px 8px;
    height: 30px;
    gap: 4px;
  }
  .universal-search-input {
    font-size: 0.8rem;
    min-width: 0;
  }
  .search-submit-btn {
    width: 24px;
    height: 24px;
    flex-shrink: 0;
  }

  /* Workspace on Mobile */
  .app-workspace {
    height: calc(100dvh - var(--header-height));
  }
  .view-pane.room-view {
    flex-direction: column;
    overflow-y: auto;
  }

  /* Player Area on Mobile: Full Width 16:9 */
  .room-player-column {
    flex: 1 1 auto;
    width: 100% !important;
    min-width: 100% !important;
  }
  .player-stage-wrap {
    width: 100%;
    max-width: 100%;
    aspect-ratio: 16 / 9;
    border-radius: 0;
  }

  /* Touch-friendly player controls */
  .player-ctrl-btn {
    min-width: 36px;
    min-height: 36px;
    padding: 6px;
  }
  .player-timeline-container {
    height: 22px;
  }
  .player-timeline-track {
    height: 5px;
  }
  .player-timeline-thumb {
    width: 14px;
    height: 14px;
  }

  /* Chat Sidebar on Mobile: Floating Slide-in Drawer */
  .room-sidebar {
    position: fixed;
    top: var(--header-height);
    right: 0;
    bottom: 0;
    width: 100% !important;
    max-width: 100% !important;
    z-index: 1000;
    box-shadow: -4px 0 24px rgba(0, 0, 0, 0.7);
    background: var(--bg-surface);
  }
  .room-sidebar.collapsed {
    display: none !important;
  }

  /* Lobby on Mobile */
  .lobby-hero {
    padding: 24px 12px;
  }
  .lobby-hero-title {
    font-size: clamp(1.4rem, 6vw, 2.2rem) !important;
    line-height: 1.25;
  }
  .lobby-hero-subtitle {
    font-size: 0.88rem;
    padding: 0 8px;
  }
  .lobby-action-buttons {
    flex-direction: column;
    width: 100%;
    gap: 8px;
    padding: 0 12px;
  }
  .btn-hero-create, .btn-hero-join {
    width: 100%;
    justify-content: center;
    padding: 12px 20px;
  }

  /* Modals on Mobile: Touch-friendly */
  .modal-dialog {
    width: 95% !important;
    max-width: 95% !important;
    max-height: 85dvh !important;
    margin: auto !important;
    border-radius: 14px !important;
  }
  .modal-dialog input, .modal-dialog select, .modal-dialog textarea {
    font-size: 16px !important; /* Prevents auto-zoom on iOS Safari */
  }

  /* Room Empty State on Mobile */
  .empty-player-placeholder {
    padding: 24px 12px;
  }
  .empty-title {
    font-size: 1.15rem;
  }
  .empty-actions-row {
    flex-wrap: wrap;
    justify-content: center;
    gap: 8px;
  }
}


/* ========================================================================== */
/* QUALITY SELECTOR MENU                                                      */
/* ========================================================================== */
.player-quality-menu-wrap {
  position: relative;
  display: inline-flex;
  align-items: center;
}
.player-quality-btn {
  font-size: 11px !important;
  font-weight: 700 !important;
  padding: 3px 8px !important;
  border-radius: 6px !important;
  background: rgba(255, 255, 255, 0.08) !important;
  border: 1px solid var(--border-color) !important;
  color: var(--text-main) !important;
  cursor: pointer;
}
.player-quality-btn:hover {
  background: rgba(255, 255, 255, 0.16) !important;
  border-color: var(--primary) !important;
}
.quality-dropdown-menu {
  position: absolute;
  bottom: 44px;
  right: 0;
  background: rgba(20, 20, 23, 0.95);
  backdrop-filter: blur(14px);
  border: 1px solid var(--border-color);
  border-radius: var(--radius-md);
  padding: 6px;
  display: none;
  flex-direction: column;
  gap: 2px;
  box-shadow: 0 8px 24px rgba(0,0,0,0.5);
  z-index: 50;
  min-width: 140px;
}
.quality-dropdown-menu.active {
  display: flex !important;
}
.quality-opt {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 7px 12px;
  border-radius: 6px;
  font-size: 0.8rem;
  color: var(--text-main);
  cursor: pointer;
  white-space: nowrap;
  transition: background 0.15s, color 0.15s;
}
.quality-opt:hover {
  background: rgba(255, 255, 255, 0.08);
}
.quality-opt.active {
  background: rgba(99, 102, 241, 0.2);
  color: #818cf8;
  font-weight: 600;
}

/* Series Episodes Drawer Button in Player */
.player-episodes-wrap {
  position: relative;
  display: inline-flex;
  align-items: center;
}
.player-episodes-wrap .player-ctrl-btn {
  padding: 3px 8px !important;
  border-radius: 6px !important;
  background: rgba(99, 102, 241, 0.15) !important;
  border: 1px solid rgba(99, 102, 241, 0.4) !important;
  color: #c7d2fe !important;
  cursor: pointer;
}
.player-episodes-wrap .player-ctrl-btn:hover {
  background: rgba(99, 102, 241, 0.3) !important;
  border-color: var(--primary) !important;
}

/* ========================================================================== */
/* MEDIA DETAILS MODAL (MOVIES & SERIES PICKER)                               */
/* ========================================================================== */
.media-header-card {
  display: flex;
  gap: 16px;
  align-items: flex-start;
  margin-bottom: 16px;
}
.media-poster-img {
  width: 95px;
  height: 140px;
  border-radius: 8px;
  object-fit: cover;
  background: #000;
  border: 1px solid var(--border-color);
  flex-shrink: 0;
  box-shadow: 0 4px 12px rgba(0,0,0,0.4);
}
.media-meta-col {
  display: flex;
  flex-direction: column;
  gap: 6px;
  flex: 1;
  min-width: 0;
}
.media-title-main {
  font-size: 1.15rem;
  font-weight: 700;
  color: var(--text-main);
  line-height: 1.3;
}
.media-badges-row {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.media-badge-tag {
  font-size: 0.72rem;
  font-weight: 600;
  padding: 2px 7px;
  border-radius: 6px;
  background: rgba(255,255,255,0.08);
  color: var(--text-main);
}
.media-desc-text {
  font-size: 0.8rem;
  color: var(--text-muted);
  line-height: 1.4;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.media-section-label {
  font-size: 0.85rem;
  font-weight: 600;
  color: var(--text-main);
  margin: 14px 0 6px 0;
  display: flex;
  align-items: center;
  gap: 6px;
}
.seasons-tabs-row {
  display: flex;
  gap: 8px;
  overflow-x: auto;
  padding-bottom: 6px;
  scrollbar-width: thin;
}
.season-tab {
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid var(--border-color);
  color: var(--text-main);
  padding: 6px 14px;
  border-radius: 18px;
  font-size: 0.82rem;
  font-weight: 600;
  cursor: pointer;
  white-space: nowrap;
  transition: background 0.15s, border-color 0.15s, color 0.15s;
}
.season-tab:hover {
  background: rgba(255, 255, 255, 0.12);
  border-color: var(--primary);
}
.season-tab.active {
  background: var(--primary);
  border-color: var(--primary);
  color: #fff;
  box-shadow: 0 2px 8px rgba(99, 102, 241, 0.4);
}

.episodes-grid-row {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(70px, 1fr));
  gap: 8px;
  max-height: 180px;
  overflow-y: auto;
  padding: 4px 2px;
  border: 1px solid rgba(255,255,255,0.06);
  border-radius: 8px;
  background: rgba(0,0,0,0.15);
}
.ep-btn {
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid var(--border-color);
  color: var(--text-main);
  padding: 8px 4px;
  border-radius: 8px;
  font-size: 0.8rem;
  font-weight: 600;
  text-align: center;
  cursor: pointer;
  transition: all 0.15s ease;
}
.ep-btn:hover {
  border-color: var(--primary);
  background: rgba(255, 255, 255, 0.1);
}
.ep-btn.active {
  background: rgba(99, 102, 241, 0.25);
  border-color: var(--primary);
  color: #818cf8;
  box-shadow: 0 0 10px rgba(99, 102, 241, 0.3);
}

.media-dub-wrap {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  max-height: 150px;
  overflow-y: auto;
  padding: 2px;
}
.media-dub-pill {
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid var(--border-color);
  color: var(--text-main);
  padding: 6px 12px;
  border-radius: 8px;
  font-size: 0.8rem;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  transition: all 0.15s ease;
}
.media-dub-pill:hover {
  border-color: var(--primary);
  background: rgba(255, 255, 255, 0.1);
}
.media-dub-pill.active {
  background: rgba(16, 185, 129, 0.18);
  border-color: #10b981;
  color: #34d399;
  font-weight: 600;
}

.vd-modal-launch-btn {
  width: 100%;
  margin-top: 18px;
  padding: 13px 18px;
  background: linear-gradient(135deg, #6366f1 0%, #4f46e5 100%);
  color: #fff;
  font-size: 0.95rem;
  font-weight: 700;
  border: none;
  border-radius: 10px;
  cursor: pointer;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  box-shadow: 0 4px 16px rgba(99, 102, 241, 0.4);
  transition: transform 0.15s, box-shadow 0.15s;
}
.vd-modal-launch-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 6px 22px rgba(99, 102, 241, 0.6);
}
.vd-modal-launch-sub {
  font-size: 0.75rem;
  font-weight: 400;
  opacity: 0.85;
  margin-top: 2px;
}

.vd-spinner {
  width: 34px;
  height: 34px;
  border: 3px solid rgba(255, 255, 255, 0.1);
  border-top-color: var(--primary);
  border-radius: 50%;
  animation: vdSpin 0.75s linear infinite;
}
@keyframes vdSpin {
  to { transform: rotate(360deg); }
}

"""
