import eventlet
eventlet.monkey_patch()
import json
import time
import uuid
import re
import os
from pathlib import Path
from typing import Dict, Any, Optional, List

import requests
from flask import Flask, render_template, request, jsonify, Response, stream_with_context
from flask_socketio import SocketIO, emit, join_room, leave_room

import urllib.parse
import ipaddress
import socket
import database
from PIL import Image, ImageOps
from video_resolver import VideoResolver, USER_AGENT

app = Flask(__name__)
app.config["SECRET_KEY"] = "rave_halloween_sync_secret_2026"
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024 * 1024  # 10 GB
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="eventlet")

STATE_FILE = Path(__file__).with_name("session_state.json")
UPLOAD_FOLDER = Path(__file__).with_name("uploads")
UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)
MAX_HISTORY = 200
MAX_ROOMS = 100
MAX_AVATAR_LEN = 120_000
MAX_MEDIA_LEN = 2_500_000
DEFAULT_ROOM_ID = "main"
ROOM_MAX_AGE = 24 * 3600  # 24 hours max lifetime
MAX_HISTORY_LINKS = 40
MAX_MOMENTS = 100

ALLOWED_REACTIONS = [
    "🎃", "👻", "🦇", "🕷️", "💀", "🍬", "🍫", "🕸️", "🕯️", "🧟",
    "❤️", "🔥", "😂", "😮", "😢", "👏", "🎉", "👀"
]

def now() -> float:
    return time.time()

def new_id(prefix: str = "m_") -> str:
    return f"{prefix}{uuid.uuid4().hex[:10]}"

def clean_text(val: Any, limit: int = 500) -> str:
    if val is None:
        return ""
    text = str(val).strip()
    return text[:limit]

def default_video() -> Dict[str, Any]:
    return {
        "url": "",
        "type": "none",
        "id": "",
        "title": "",
        "poster": "",
        "duration": 0.0,
        "playing": False,
        "time": 0.0,
        "updated_at": now(),
        "seq": 0,
        "source_sid": "",
        "source_name": "",
        "audio_names": [],
        "selected_audio": 0,
    }

def default_room_extras() -> Dict[str, Any]:
    return {
        "history": [],
        "moments": [],
        "queue": [],
    }

def make_room(name: str = "Общая", private: bool = False, code: str = "", owner: str = "") -> tuple[str, Dict[str, Any]]:
    room_id = new_id("r_")
    return room_id, {
        "id": room_id,
        "name": clean_text(name, 40) or "Комната",
        "private": bool(private),
        "code": clean_text(code, 64),
        "owner": clean_text(owner, 64),
        "leader_sid": "",
        "created_at": now(),
        "video": default_video(),
        "chat": [],
        **default_room_extras(),
    }

state: Dict[str, Any] = {
    "version": 3,
    "accounts": {},
    "rooms": {
        DEFAULT_ROOM_ID: {
            "id": DEFAULT_ROOM_ID,
            "name": "Общая",
            "private": False,
            "code": "",
            "owner": "",
            "leader_sid": "",
            "created_at": now(),
            "video": default_video(),
            "chat": [],
            **default_room_extras(),
        }
    },
    "room_order": [DEFAULT_ROOM_ID],
}
sessions: Dict[str, Dict[str, Any]] = {}
LOCAL_DISK_FILES: Dict[str, Dict[str, Any]] = {}

_state_dirty = False
_last_save_time = 0.0

def mark_dirty():
    global _state_dirty
    _state_dirty = True

def flush_state(force: bool = False):
    global _state_dirty, _last_save_time
    if not _state_dirty and not force:
        return
    cur = now()
    if not force and (cur - _last_save_time < 4.0):
        return
    _state_dirty = False
    _last_save_time = cur

    payload = {
        "version": 3,
        "accounts": state["accounts"],
        "rooms": state["rooms"],
        "room_order": state["room_order"][-MAX_ROOMS:],
        "disk_tokens": state.get("disk_tokens", {}),
        "recent_disk_files": state.get("recent_disk_files", []),
    }
    try:
        tmp = STATE_FILE.with_suffix(".tmp")
        tmp.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        tmp.replace(STATE_FILE)
    except OSError:
        pass

def legacy_account_id(nick: str) -> str:
    nick = clean_text(nick, 24) or "Гость"
    return "legacy_" + uuid.uuid5(uuid.NAMESPACE_DNS, nick).hex[:12]

def ensure_legacy_account(nick: str, avatar: str = "") -> str:
    account_id = legacy_account_id(nick)
    if account_id not in state["accounts"]:
        state["accounts"][account_id] = {
            "id": account_id,
            "nick": clean_text(nick, 24) or "Гость",
            "avatar": avatar if str(avatar).startswith("data:image/") else "",
            "created_at": now(),
            "updated_at": now(),
        }
        mark_dirty()
    elif avatar and str(avatar).startswith("data:image/"):
        state["accounts"][account_id]["avatar"] = avatar
        mark_dirty()
    return account_id

def normalize_reactions(reactions: Any) -> Dict[str, list]:
    if not isinstance(reactions, dict):
        return {}
    out = {}
    for emoji, users in reactions.items():
        if isinstance(users, list):
            out[emoji] = users
        elif isinstance(users, int) and users > 0:
            out[emoji] = [f"legacy_{i}" for i in range(users)]
    return out

def normalize_message(item: Any) -> Optional[Dict[str, Any]]:
    if not isinstance(item, dict):
        return None
    kind = item.get("kind") or "message"
    account_id = clean_text(item.get("account_id"), 64)
    if not account_id:
        account_id = ensure_legacy_account(item.get("nick") or "Гость")

    reply = item.get("reply")
    if isinstance(reply, dict):
        reply_account_id = clean_text(reply.get("account_id"), 64)
        if not reply_account_id:
            reply_account_id = ensure_legacy_account(reply.get("nick") or "Гость")
        reply = {
            "id": clean_text(reply.get("id"), 64),
            "account_id": reply_account_id,
            "text": clean_text(reply.get("text"), 160),
        }
    else:
        reply = None

    base = {
        "id": clean_text(item.get("id"), 64) or new_id("m_"),
        "kind": kind if kind in ("message", "media", "reaction", "system") else "message",
        "account_id": account_id,
        "reply": reply,
        "reactions": normalize_reactions(item.get("reactions")),
        "ts": float(item.get("ts") or now()),
    }
    if base["kind"] == "media":
        base["src"] = clean_text(item.get("src"), MAX_MEDIA_LEN)
    elif base["kind"] == "reaction":
        base["text"] = clean_text(item.get("emoji") or item.get("text"), 8)
    else:
        base["text"] = clean_text(item.get("text"), 800)
    return base

def normalize_loaded_state(data: Any):
    if not isinstance(data, dict):
        return

    if isinstance(data.get("rooms"), dict):
        state["accounts"] = data.get("accounts", {}) if isinstance(data.get("accounts"), dict) else {}
        state["rooms"] = data["rooms"] or state["rooms"]
        state["room_order"] = data.get("room_order") or list(state["rooms"].keys())
        if isinstance(data.get("disk_tokens"), dict):
            state["disk_tokens"] = data["disk_tokens"]
            LOCAL_DISK_FILES.update(data["disk_tokens"])
        if isinstance(data.get("recent_disk_files"), list):
            state["recent_disk_files"] = data["recent_disk_files"]
        for room in state["rooms"].values():
            vid = default_video()
            if isinstance(room.get("video"), dict):
                vid.update(room["video"])
            room["video"] = vid
            room.setdefault("owner", "")
            room.setdefault("leader_sid", "")
            room.setdefault("private", False)
            room.setdefault("code", "")
            room.setdefault("history", [])
            room.setdefault("moments", [])
            room["chat"] = [m for m in (normalize_message(x) for x in room.get("chat", [])) if m][-MAX_HISTORY:]
            room["history"] = room.get("history", [])[-MAX_HISTORY_LINKS:]
            room["moments"] = room.get("moments", [])[-MAX_MOMENTS:]
    else:
        main = state["rooms"][DEFAULT_ROOM_ID]
        if isinstance(data.get("video"), dict):
            main["video"].update(data["video"])
        if isinstance(data.get("avatars"), dict):
            for nick, avatar in data["avatars"].items():
                ensure_legacy_account(nick, avatar)
        if isinstance(data.get("chat"), list):
            main["chat"] = [m for m in (normalize_message(x) for x in data["chat"]) if m][-MAX_HISTORY:]

    if DEFAULT_ROOM_ID not in state["rooms"]:
        state["rooms"][DEFAULT_ROOM_ID] = make_room("Общая")[1]
    if DEFAULT_ROOM_ID not in state["room_order"]:
        state["room_order"].insert(0, DEFAULT_ROOM_ID)

def load_state():
    if not STATE_FILE.exists():
        return
    try:
        normalize_loaded_state(json.loads(STATE_FILE.read_text(encoding="utf-8")))
    except (OSError, json.JSONDecodeError):
        pass

def room_channel(room_id: str) -> str:
    return f"room:{room_id}"

def room_online(room_id: str) -> int:
    return sum(1 for item in sessions.values() if item.get("room_id") == room_id)

def room_members(room_id: str) -> List[Dict[str, str]]:
    members = []
    seen = set()
    for s in sessions.values():
        if s.get("room_id") == room_id:
            acc_id = s.get("account_id") or s.get("sid")
            if acc_id and acc_id not in seen:
                seen.add(acc_id)
                acc = state["accounts"].get(acc_id, {})
                nick = s.get("user_name") or acc.get("nick") or acc.get("name")
                avatar = s.get("avatar") or acc.get("avatar") or ""
                if (not avatar or not nick or nick == "Участник") and acc_id and str(acc_id).isdigit():
                    try:
                        u = database.get_user_by_id(int(acc_id))
                        if u:
                            nick = nick or u.get("display_name") or u.get("username")
                            avatar = avatar or u.get("avatar") or ""
                    except Exception:
                        pass
                nick = nick or "Участник"
                members.append({
                    "id": acc_id,
                    "nick": nick,
                    "name": nick,
                    "avatar": avatar,
                    "is_buffering": bool(s.get("is_buffering", False))
                })
    if not members:
        room = state["rooms"].get(room_id)
        owner_id = room.get("owner") if room else None
        if owner_id:
            acc = state["accounts"].get(owner_id, {})
            nick = acc.get("nick") or acc.get("name") or "Хост"
            members.append({
                "id": owner_id,
                "nick": nick,
                "name": nick,
                "avatar": acc.get("avatar") or ""
            })
    return members

def cleanup_expired_rooms() -> int:
    cur = now()
    expired = []
    for room_id, room in list(state["rooms"].items()):
        if room_id == DEFAULT_ROOM_ID:
            continue
        created = float(room.get("created_at") or 0.0)
        # Max lifetime: 24 hours (86400 seconds)
        if created <= 0.0 or (cur - created > ROOM_MAX_AGE):
            expired.append(room_id)

    if expired:
        for rid in expired:
            state["rooms"].pop(rid, None)
            if rid in state["room_order"]:
                state["room_order"].remove(rid)
        mark_dirty()
    return len(expired)

def public_room(room: Dict[str, Any]) -> Dict[str, Any]:
    vid = current_video(room)
    created = float(room.get("created_at") or now())
    age_seconds = max(0.0, now() - created)
    expires_in_seconds = max(0, int(ROOM_MAX_AGE - age_seconds))
    hours_left = max(1, int(round(expires_in_seconds / 3600.0)))
    return {
        "id": room["id"],
        "name": room.get("name") or room.get("title") or "Комната",
        "title": room.get("name") or room.get("title") or "Комната",
        "private": bool(room.get("private", False)),
        "owner": room.get("owner", ""),
        "online": room_online(room["id"]),
        "members": room_members(room["id"]),
        "chat_count": len(room.get("chat", [])),
        "video": vid,
        "playing": bool(vid.get("playing")),
        "video_title": vid.get("title") or "",
        "video_poster": vid.get("poster") or "",
        "video_type": vid.get("type") or "none",
        "created_at": created,
        "expires_in_seconds": expires_in_seconds,
        "hours_left": hours_left,
    }

def visible_rooms():
    cleanup_expired_rooms()
    rooms = []
    for room_id in list(state["room_order"]):
        room = state["rooms"].get(room_id)
        if room and not room.get("private"):
            if room_id == DEFAULT_ROOM_ID and room_online(room_id) == 0:
                continue
            rooms.append(public_room(room))
    return rooms

def current_video(room: Dict[str, Any]) -> Dict[str, Any]:
    video = dict(room.get("video") or default_video())
    url = video.get("url") or ""
    # Direct streams play unproxied

    if video.get("playing"):
        elapsed = now() - float(video.get("updated_at") or now())
        current_t = max(0.0, float(video.get("time") or 0.0) + elapsed)
        dur = float(video.get("duration") or 0.0)
        if dur > 0.0 and current_t >= dur:
            video["time"] = dur
            video["playing"] = False
        else:
            video["time"] = current_t
    return video

def current_session() -> Dict[str, Any]:
    return sessions.setdefault(request.sid, {"sid": request.sid, "account_id": "", "room_id": "", "user_name": "", "avatar": ""})

def current_room() -> Optional[Dict[str, Any]]:
    room_id = current_session().get("room_id")
    return state["rooms"].get(room_id or "")

def current_user_name() -> str:
    s = current_session()
    if s.get("user_name"):
        return s["user_name"]
    acc_id = s.get("account_id")
    if acc_id and acc_id in state["accounts"]:
        return state["accounts"][acc_id].get("nick") or state["accounts"][acc_id].get("name") or "Участник"
    return "Гость"

def elect_room_leader(room: Dict[str, Any]):
    current_leader = room.get("leader_sid")
    if current_leader and current_leader in sessions and sessions[current_leader].get("room_id") == room["id"]:
        return
    room_sids = [sid for sid, s in sessions.items() if s.get("room_id") == room["id"]]
    if room_sids:
        room["leader_sid"] = room_sids[0]
    else:
        room["leader_sid"] = ""

def emit_room_list():
    emit("rooms_list", visible_rooms())

def emit_room_state(room: Dict[str, Any], include_self: bool = True, to_sid: Optional[str] = None):
    elect_room_leader(room)
    payload = {
        "room": public_room(room),
        "video": current_video(room),
        "chat": room.get("chat", [])[-MAX_HISTORY:],
        "history": room.get("history", [])[-MAX_HISTORY_LINKS:],
        "moments": room.get("moments", [])[-MAX_MOMENTS:],
        "queue": room.get("queue", []),
        "accounts": state["accounts"],
        "online": room_online(room["id"]),
        "server_time": now(),
        "leader_sid": room.get("leader_sid", ""),
        "is_leader": (to_sid == room.get("leader_sid")) if to_sid else False,
    }
    if to_sid:
        emit("room_state", payload, to=to_sid)
    else:
        emit("room_state", payload, to=room_channel(room["id"]), include_self=include_self)

def require_room(data: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    session = current_session()
    room_id = session.get("room_id")
    if data and isinstance(data, dict) and data.get("room_id"):
        explicit_room_id = clean_text(data.get("room_id"), 64)
        if explicit_room_id in state["rooms"]:
            if room_id and room_id != explicit_room_id:
                try:
                    leave_room(room_channel(room_id))
                except Exception:
                    pass
            room_id = explicit_room_id
            session["room_id"] = room_id

    if not room_id or room_id not in state["rooms"]:
        emit("room_error", {"message": "Вы не в комнате"})
        return None

    try:
        join_room(room_channel(room_id))
    except Exception:
        pass
    return state["rooms"][room_id]
def remember_message(room: Dict[str, Any], item: Dict[str, Any]):
    room.setdefault("chat", []).append(item)
    del room["chat"][:-MAX_HISTORY]
    mark_dirty()

def remember_video(room: Dict[str, Any], video: Dict[str, Any]):
    if video.get("type") == "none" or not video.get("url"):
        return
    item = {
        "id": new_id("v_"),
        "url": clean_text(video.get("url"), 2000),
        "type": clean_text(video.get("type"), 16),
        "video_id": clean_text(video.get("id"), 64),
        "title": clean_text(video.get("title"), 120),
        "poster": clean_text(video.get("poster"), 500),
        "duration": float(video.get("duration", 0.0)),
        "ts": now(),
    }
    history = room.setdefault("history", [])
    history = [h for h in history if h.get("url") != item["url"]]
    history.insert(0, item)
    room["history"] = history[:MAX_HISTORY_LINKS]
    mark_dirty()

def background_save_loop():
    while True:
        time.sleep(2.0)
        cleanup_expired_rooms()
        flush_state()

eventlet.spawn(background_save_loop)

def background_keepalive_loop():
    time.sleep(30.0)
    while True:
        try:
            ext_url = os.environ.get("RENDER_EXTERNAL_URL") or "https://vd-site.onrender.com"
            requests.get(f"{ext_url}/ping", timeout=10)
        except Exception:
            pass
        time.sleep(600.0)

eventlet.spawn(background_keepalive_loop)
load_state()

# ---------------- HTTP ROUTES ----------------

@app.after_request
def add_header(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

@app.route("/")
@app.route("/room/<room_id>")
@app.route("/<room_id>")
def index(room_id=None):
    return render_template("index.html", asset_version=int(time.time()))

@app.route("/api/ping")
def api_ping():
    return jsonify({
        "status": "ok",
        "pong": True,
        "server_time": now()
    })

@app.route("/api/rooms")
def api_rooms():
    return jsonify({"rooms": visible_rooms()})

@app.route("/api/featured")
def api_featured():
    return jsonify(VideoResolver.get_featured_content())

@app.route("/api/search_movie")
def api_search_movie():
    title = request.args.get("title", "").strip()
    if not title:
        return jsonify({"error": "Empty title"}), 400
    return jsonify(VideoResolver.resolve_movie_by_title(title))

@app.route("/api/catalog")
def api_catalog():
    lang = request.args.get("lang", "ua")
    return jsonify(VideoResolver.get_catalog_shows(lang))

@app.route("/api/project")
def api_project():
    type_slug = request.args.get("type") or request.args.get("typeSlug") or "show"
    channel_slug = request.args.get("channel") or request.args.get("channelSlug") or "novyy-kanal"
    project_slug = request.args.get("project") or request.args.get("projectSlug") or request.args.get("slug") or ""
    lang = request.args.get("lang", "ua")
    if not project_slug:
        return jsonify({"error": "Missing project"}), 400
    return jsonify(VideoResolver.get_project_details(type_slug, channel_slug, project_slug, lang))

@app.route("/api/project/<slug>")
def api_project_by_slug(slug):
    slug_lower = slug.lower()
    if "budyn" in slug_lower or "будинок" in slug_lower or slug_lower in ("domik", "budynochok"):
        return jsonify(VideoResolver.get_project_details("serials", "novyy-kanal", "domik", "ua"))
    elif "supermama" in slug_lower or "супермама" in slug_lower:
        return jsonify(VideoResolver.get_project_details("show", "stb", "supermama", "ua"))
    else:
        return jsonify(VideoResolver.get_project_details("show", "stb", slug, "ua"))

@app.route("/api/catalog/search")
def api_catalog_search():
    q = request.args.get("q", "").strip()
    limit = int(request.args.get("limit", 15))
    return jsonify({"results": VideoResolver.search_catalog(q, limit=limit)})

@app.route("/api/catalog/details")
def api_catalog_details():
    kp_id = request.args.get("kp", "").strip()
    imdb_id = request.args.get("imdb", "").strip()
    return jsonify(VideoResolver.get_media_details(kp_id=kp_id, imdb_id=imdb_id))

@app.route("/api/catalog/stream")
def api_catalog_stream():
    kp_id = request.args.get("kp", "").strip()
    imdb_id = request.args.get("imdb", "").strip()
    season = request.args.get("season")
    episode = request.args.get("episode")
    title = request.args.get("title", "").strip()
    if season is not None:
        try:
            season = int(season)
        except ValueError:
            pass
    return jsonify(VideoResolver.resolve_stream_for_play(kp_id=kp_id, imdb_id=imdb_id, season=season, episode=episode, title=title))

# ================================= AUTH & USER ACCOUNTS API =================================

def get_current_user() -> Optional[Dict[str, Any]]:
    token = request.cookies.get("vd_token") or request.cookies.get("rave_token")
    if not token:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:].strip()
    if token:
        return database.get_user_by_session(token)
    return None

@app.route("/api/auth/register", methods=["POST"])
def api_auth_register():
    client_ip = request.headers.get("X-Forwarded-For", request.remote_addr).split(",")[0].strip()
    if not check_rate_limit(f"reg_{client_ip}", max_requests=5, window_sec=60):
        return jsonify({"error": "Слишком много попыток регистрации. Подождите 1 минуту."}), 429
    data = request.get_json(silent=True) or {}
    username = clean_text(data.get("username", ""), 30).strip()
    display_name = clean_text(data.get("display_name", ""), 60).strip()
    password = str(data.get("password") or "")

    if not username or not password:
        return jsonify({"error": "Логин и пароль обязательны"}), 400

    try:
        user = database.create_user(username, display_name or username, password)
        token = database.create_session(user["id"])
        stats = database.get_user_stats(user["id"])
        resp = jsonify({"success": True, "user": user, "stats": stats, "token": token})
        resp.set_cookie("vd_token", token, max_age=30*86400, samesite="Lax", httponly=False)
        resp.set_cookie("rave_token", token, max_age=30*86400, samesite="Lax", httponly=False)
        return resp
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"Ошибка регистрации: {e}"}), 500

@app.route("/api/auth/login", methods=["POST"])
def api_auth_login():
    client_ip = request.headers.get("X-Forwarded-For", request.remote_addr).split(",")[0].strip()
    if not check_rate_limit(f"login_{client_ip}", max_requests=10, window_sec=60):
        return jsonify({"error": "Слишком много попыток входа. Подождите 1 минуту."}), 429
    data = request.get_json(silent=True) or {}
    username = clean_text(data.get("username", ""), 30).strip()
    password = str(data.get("password") or "")

    if not username or not password:
        return jsonify({"error": "Введите логин и пароль"}), 400

    user = database.authenticate_user(username, password)
    if not user:
        return jsonify({"error": "Неверный логин или пароль"}), 401

    token = database.create_session(user["id"])
    stats = database.get_user_stats(user["id"])
    history = database.get_user_watch_history(user["id"], limit=15)
    resp = jsonify({"success": True, "user": user, "stats": stats, "history": history, "token": token})
    resp.set_cookie("vd_token", token, max_age=30*86400, samesite="Lax", httponly=False)
    resp.set_cookie("rave_token", token, max_age=30*86400, samesite="Lax", httponly=False)
    return resp

@app.route("/api/auth/logout", methods=["POST"])
def api_auth_logout():
    token = request.cookies.get("rave_token")
    if token:
        database.delete_session(token)
    resp = jsonify({"success": True})
    resp.delete_cookie("rave_token")
    return resp

@app.route("/api/auth/self_heal", methods=["POST"])
def api_auth_self_heal():
    data = request.get_json(silent=True) or {}
    profile = data.get("profile") or {}
    creds = data.get("creds") or {}

    username = clean_text(profile.get("username") or creds.get("username") or "", 30).strip().lower()
    if not username:
        return jsonify({"success": False, "error": "No username"}), 400

    user = database.get_user_by_username(username)
    if not user:
        display_name = clean_text(profile.get("display_name") or username, 60).strip()
        pwd = str(creds.get("password") or "vd_pass_2026")
        avatar = str(profile.get("avatar") or "")
        try:
            user = database.create_user(username, display_name, pwd, avatar=avatar)
            if profile.get("bio"):
                database.update_user_profile(user["id"], bio=profile.get("bio"))
            if profile.get("banner_color"):
                database.update_user_profile(user["id"], banner_color=profile.get("banner_color"))
        except Exception:
            user = database.get_user_by_username(username)
            if not user:
                return jsonify({"success": False, "error": "Failed to restore user"}), 400

    token = database.create_session(user["id"])
    stats = database.get_user_stats(user["id"])
    history = database.get_user_watch_history(user["id"], limit=15)
    resp = jsonify({"success": True, "user": user, "stats": stats, "history": history, "token": token})
    resp.set_cookie("vd_token", token, max_age=30*86400, samesite="Lax", httponly=False)
    resp.set_cookie("rave_token", token, max_age=30*86400, samesite="Lax", httponly=False)
    return resp

@app.route("/api/auth/me")
def api_auth_me():
    user = get_current_user()
    if not user:
        return jsonify({"authenticated": False, "user": None})

    stats = database.get_user_stats(user["id"])
    history = database.get_user_watch_history(user["id"], limit=15)
    return jsonify({"authenticated": True, "user": user, "stats": stats, "history": history})

@app.route("/api/auth/profile", methods=["GET", "POST"])
def api_auth_profile():
    if request.method == "GET":
        return api_auth_me()
    user = get_current_user()
    if not user:
        return jsonify({"error": "Не авторизован"}), 401

    data = request.get_json(silent=True) or {}
    display_name = data.get("display_name")
    bio = data.get("bio")
    banner_color = data.get("banner_color")
    avatar = data.get("avatar")
    status = data.get("status")

    updated = database.update_user_profile(
        user["id"],
        display_name=display_name,
        bio=bio,
        avatar=avatar,
        banner_color=banner_color,
        status=status
    )
    return jsonify({"success": True, "user": updated})

@app.route("/api/auth/avatar", methods=["POST"])
def api_auth_avatar():
    user = get_current_user()
    if not user:
        return jsonify({"error": "Требуется авторизация"}), 401

    avatar_preset = request.form.get("avatar_url") or (request.get_json(silent=True) or {}).get("avatar_url")
    if avatar_preset:
        updated = database.update_user_profile(user["id"], avatar=avatar_preset)
        socketio.emit("friend_activity_update", {"type": "avatar_updated", "user_id": user["id"]})
        return jsonify({"success": True, "user": updated, "avatar": avatar_preset})

    file = request.files.get("avatar") or request.files.get("file")
    if not file or not file.filename:
        return jsonify({"error": "Файл не передан"}), 400

    try:
        img = Image.open(file)
        img = ImageOps.exif_transpose(img)
        if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
            img = img.convert("RGBA")
        else:
            img = img.convert("RGB")

        w, h = img.size
        min_dim = min(w, h)
        left = (w - min_dim) // 2
        top = (h - min_dim) // 2
        img = img.crop((left, top, left + min_dim, top + min_dim))
        img = img.resize((256, 256), Image.Resampling.LANCZOS)

        avatar_dir = Path(__file__).resolve().parent / "static" / "avatars"
        avatar_dir.mkdir(parents=True, exist_ok=True)
        filename = f"user_{user['id']}_{int(time.time())}.webp"
        save_path = avatar_dir / filename
        img.save(str(save_path), "WEBP", quality=85)

        avatar_url = f"/static/avatars/{filename}"
        updated = database.update_user_profile(user["id"], avatar=avatar_url)
        socketio.emit("friend_activity_update", {"type": "avatar_updated", "user_id": user["id"]})
        return jsonify({"success": True, "user": updated, "avatar": avatar_url})
    except Exception as e:
        return jsonify({"error": f"Ошибка обработки изображения: {e}"}), 400

@app.route("/api/watch/heartbeat", methods=["POST"])
def api_watch_heartbeat():
    data = request.get_json(silent=True) or {}
    user = get_current_user()
    if not user:
        return jsonify({"status": "guest", "logged_in": False})

    try:
        delta = max(1, min(int(data.get("delta", 15)), 30))
    except (ValueError, TypeError):
        delta = 15

    title = clean_text(data.get("title", ""), 150)
    poster = clean_text(data.get("poster", ""), 500)
    url = clean_text(data.get("url", ""), 2000)
    media_type = clean_text(data.get("media_type", "movie"), 20)
    duration = int(float(data.get("duration") or 0))

    stats = database.record_watch_time(
        user["id"],
        seconds_delta=delta,
        video_title=title,
        video_poster=poster,
        video_url=url,
        media_type=media_type,
        duration=duration
    )
    return jsonify({"status": "ok", "logged_in": True, "stats": stats})

@app.route("/api/user/<username>")
def api_user_public(username):
    user = database.get_user_by_username(username)
    if not user:
        return jsonify({"error": "Пользователь не найден"}), 404

    stats = database.get_user_stats(user["id"])
    history = database.get_user_watch_history(user["id"], limit=10)
    safe_user = {
        "id": user["id"],
        "username": user["username"],
        "display_name": user["display_name"],
        "avatar": user["avatar"],
        "banner_color": user.get("banner_color", "#8b5cf6"),
        "bio": user.get("bio", ""),
        "role": user.get("role", "user"),
        "status": user.get("status", "online"),
        "created_at": user["created_at"],
    }
    return jsonify({"user": safe_user, "stats": stats, "history": history})


@app.route("/api/friends")
def api_friends():
    user = get_current_user()
    if not user:
        return jsonify({"friends": [], "authenticated": False})

    friends_list = database.get_user_friends(user["id"])
    
    # Determine strictly live online users from active socket connections
    connected_uids = set()
    for s in sessions.values():
        acc = s.get("account_id")
        if acc:
            connected_uids.add(str(acc))
        db_id = s.get("db_user_id")
        if db_id:
            connected_uids.add(str(db_id))

    result = []
    for f in friends_list:
        fid = f["id"]
        is_online = str(fid) in connected_uids
        active_room = None

        if is_online:
            candidate_rooms = []
            for r_id, r in state.get("rooms", {}).items():
                members = room_members(r_id)
                is_active_member = any(str(m.get("account_id")) == str(fid) or m.get("name") == f.get("display_name") for m in members)
                is_owner = (str(r.get("owner")) == str(fid))
                if is_active_member or is_owner:
                    candidate_rooms.append((1 if is_active_member else 0, r.get("last_active", 0), r_id, r, members))

            if candidate_rooms:
                candidate_rooms.sort(key=lambda x: (x[0], x[1]), reverse=True)
                _, _, r_id, r, members = candidate_rooms[0]
                v = r.get("video") or {}
                active_room = {
                    "room_id": r_id,
                    "title": r.get("title") or r.get("name") or "Комната",
                    "video_title": v.get("title") or "Видео",
                    "video_poster": v.get("poster") or "",
                    "video_url": v.get("url") or "",
                    "playing": bool(v.get("playing", False)),
                    "current_time": v.get("current_time", 0),
                    "members_count": len(members),
                    "code": r.get("code", "")
                }

        result.append({
            "id": fid,
            "username": f["username"],
            "display_name": f["display_name"],
            "avatar": f["avatar"],
            "is_online": is_online,
            "active_room": active_room
        })

    return jsonify({"friends": result, "authenticated": True, "count": len(result)})

@app.route("/api/friends/add", methods=["POST"])
def api_friends_add():
    user = get_current_user()
    if not user:
        return jsonify({"error": "Требуется авторизация"}), 401
    data = request.get_json(silent=True) or {}
    friend_username = clean_text(data.get("username", ""), 40).strip()
    if not friend_username:
        return jsonify({"error": "Укажите имя друга"}), 400
    friend = database.add_friend_by_username(user["id"], friend_username)
    if not friend:
        return jsonify({"error": "Пользователь не найден или нельзя добавить самого себя"}), 404
    socketio.emit("friend_activity_update", {"type": "friend_added"})
    return jsonify({"success": True, "friend": {
        "id": friend["id"],
        "username": friend["username"],
        "display_name": friend["display_name"],
        "avatar": friend["avatar"]
    }})

@app.route("/api/friends/remove", methods=["POST"])
def api_friends_remove():
    user = get_current_user()
    if not user:
        return jsonify({"error": "Требуется авторизация"}), 401
    data = request.get_json(silent=True) or {}
    friend_id = data.get("friend_id")
    if not friend_id:
        return jsonify({"error": "Не указан ID друга"}), 400
    try:
        fid = int(friend_id)
        database.remove_friendship(user["id"], fid)
        socketio.emit("friend_activity_update", {"type": "friend_removed"})
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route("/api/friends/invite", methods=["POST"])
def api_friends_invite():
    user = get_current_user()
    if not user:
        return jsonify({"error": "Требуется авторизация"}), 401
    data = request.get_json(silent=True) or {}
    room_id = clean_text(data.get("room_id"), 64)
    if not room_id or room_id not in state.get("rooms", {}):
        return jsonify({"error": "Комната не найдена"}), 404

    room = state["rooms"][room_id]
    video = room.get("video") or {}
    v_title = video.get("title") or "Видео"

    target_friend_id = data.get("friend_id")
    friends = database.get_user_friends(user["id"])
    invited_count = 0

    invite_payload = {
        "from_id": user["id"],
        "from_name": user.get("display_name") or user.get("username"),
        "from_avatar": user.get("avatar") or "",
        "room_id": room_id,
        "room_title": room.get("title") or room.get("name") or "Кинозал",
        "video_title": v_title,
        "code": room.get("code", ""),
        "timestamp": time.time()
    }

    if target_friend_id:
        try:
            tfid = int(target_friend_id)
            p = {**invite_payload, "target_id": tfid}
            socketio.emit("friend_invite_received", p, to=f"user_{tfid}")
            socketio.emit("friend_invite_received", p)
            invited_count = 1
        except Exception:
            pass
    else:
        for f in friends:
            p = {**invite_payload, "target_id": f["id"]}
            socketio.emit("friend_invite_received", p, to=f"user_{f['id']}")
            socketio.emit("friend_invite_received", p)
            invited_count += 1

    return jsonify({"success": True, "invited": invited_count})


@app.route("/api/search")
def api_search():
    q = request.args.get("q", "").strip()
    if not q:
        return jsonify({"results": VideoResolver.search_catalog("", limit=15)})
    if q.startswith("http://") or q.startswith("https://"):
        resolved = VideoResolver.resolve(q)
        if resolved.get("type") != "none":
            return jsonify({"results": [resolved]})
    return jsonify({"results": VideoResolver.search_catalog(q, limit=15)})

@app.route("/api/resolve_hash")
def api_resolve_hash():
    hash_val = request.args.get("hash", "").strip()
    if not hash_val:
        return jsonify({"error": "Missing hash"}), 400
    referer = request.args.get("referer", "https://teleportal.ua")
    res = VideoResolver.resolve_starlight_hash(hash_val, referer=referer)
    if res:
        return jsonify(res)
    return jsonify({"error": "Hash not resolved"}), 404

@app.route("/api/resolve", methods=["POST"])
def api_resolve():
    data = request.get_json(silent=True) or {}
    url = str(data.get("url") or "").strip()
    if not url:
        return jsonify({"error": "Missing url"}), 400
    res = VideoResolver.resolve(url)
    return jsonify(res)

def rewrite_m3u8(playlist_text: str, base_url: str, proxy_prefix: str = "/api/hls/proxy?url=") -> str:
    lines = playlist_text.splitlines()
    new_lines = []
    for line in lines:
        sline = line.strip()
        if not sline:
            new_lines.append(line)
            continue

        if sline.startswith("#EXT-X-MEDIA:") and 'URI="' in sline:
            def repl_uri(m):
                orig_uri = m.group(1)
                full_uri = urllib.parse.urljoin(base_url, orig_uri)
                proxied = proxy_prefix + urllib.parse.quote(full_uri, safe='')
                return f'URI="{proxied}"'
            new_lines.append(re.sub(r'URI="([^"]+)"', repl_uri, sline))
            continue

        if sline.startswith("#EXT-X-KEY:") and 'URI="' in sline:
            def repl_key(m):
                orig_uri = m.group(1)
                full_uri = urllib.parse.urljoin(base_url, orig_uri)
                proxied = proxy_prefix + urllib.parse.quote(full_uri, safe='')
                return f'URI="{proxied}"'
            new_lines.append(re.sub(r'URI="([^"]+)"', repl_key, sline))
            continue

        if sline.startswith("#"):
            new_lines.append(sline)
            continue

        full_uri = urllib.parse.urljoin(base_url, sline)
        proxied = proxy_prefix + urllib.parse.quote(full_uri, safe='')
        new_lines.append(proxied)

    return "\n".join(new_lines)

# ================= SECURITY HARDENING: SSRF & RATE LIMITING =================
_SAFE_PROXY_CACHE = {}
_RATE_LIMITS = {}

def check_rate_limit(key: str, max_requests: int, window_sec: float) -> bool:
    """Sliding-window rate limiter for sensitive endpoints."""
    now_ts = time.time()
    records = _RATE_LIMITS.setdefault(key, [])
    records = [t for t in records if now_ts - t < window_sec]
    if len(records) >= max_requests:
        _RATE_LIMITS[key] = records
        return False
    records.append(now_ts)
    _RATE_LIMITS[key] = records
    return True

def is_safe_proxy_url(url: str) -> bool:
    """Blocks loopback, RFC1918 private IPs, link-local and internal hostnames to prevent SSRF."""
    try:
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return False
        hostname = (parsed.hostname or "").strip().lower()
        if not hostname:
            return False

        now_ts = time.time()
        cached = _SAFE_PROXY_CACHE.get(hostname)
        if cached and now_ts < cached[1]:
            return cached[0]

        if (
            hostname in ("localhost", "127.0.0.1", "::1", "metadata.google.internal")
            or hostname.endswith(".local")
            or hostname.endswith(".internal")
        ):
            _SAFE_PROXY_CACHE[hostname] = (False, now_ts + 300)
            return False

        try:
            addr_info = socket.getaddrinfo(hostname, None)
            for item in addr_info:
                ip_str = item[4][0]
                ip_obj = ipaddress.ip_address(ip_str)
                if (
                    ip_obj.is_private
                    or ip_obj.is_loopback
                    or ip_obj.is_link_local
                    or ip_obj.is_multicast
                    or ip_obj.is_reserved
                    or ip_obj.is_unspecified
                ):
                    _SAFE_PROXY_CACHE[hostname] = (False, now_ts + 300)
                    return False
        except socket.gaierror:
            _SAFE_PROXY_CACHE[hostname] = (False, now_ts + 300)
            return False

        _SAFE_PROXY_CACHE[hostname] = (True, now_ts + 3600)
        return True
    except Exception:
        return False
@app.route("/api/hls/proxy")
def api_hls_proxy():
    target_url = request.args.get("url", "").strip()
    if not target_url or not is_safe_proxy_url(target_url):
        return "Invalid or restricted stream URL", 400

    headers = {
        "User-Agent": USER_AGENT,
        "Referer": "https://api.namy.ws/",
        "Origin": "https://api.namy.ws",
    }
    range_header = request.headers.get("Range")
    if range_header:
        headers["Range"] = range_header

    try:
        is_m3u8 = ".m3u8" in target_url.lower()

        if is_m3u8:
            r = requests.get(target_url, headers=headers, timeout=10)
            body = rewrite_m3u8(r.text, target_url, proxy_prefix="/api/hls/proxy?url=")
            resp = Response(body, status=r.status_code, mimetype="application/vnd.apple.mpegurl")
            resp.headers["Access-Control-Allow-Origin"] = "*"
            resp.headers["Access-Control-Allow-Headers"] = "*"
            resp.headers["Cache-Control"] = "no-cache"
            return resp

        r = requests.get(target_url, headers=headers, stream=True, timeout=15)
        def generate():
            for chunk in r.iter_content(chunk_size=64 * 1024):
                if chunk:
                    yield chunk

        resp = Response(stream_with_context(generate()), status=r.status_code, mimetype=r.headers.get("Content-Type", "video/mp2t"))
        resp.headers["Access-Control-Allow-Origin"] = "*"
        resp.headers["Access-Control-Allow-Headers"] = "*"
        if "Content-Length" in r.headers:
            resp.headers["Content-Length"] = r.headers["Content-Length"]
        if "Content-Range" in r.headers:
            resp.headers["Content-Range"] = r.headers["Content-Range"]
        if "Accept-Ranges" in r.headers:
            resp.headers["Accept-Ranges"] = r.headers["Accept-Ranges"]
        return resp
    except Exception as e:
        return f"Proxy error: {e}", 502

@app.route("/api/proxy/stream")
def api_proxy_stream():
    target_url = request.args.get("url", "").strip()
    if not target_url or not is_safe_proxy_url(target_url):
        return "Invalid or restricted stream URL", 400
    headers = {"User-Agent": USER_AGENT}
    range_header = request.headers.get("Range")
    if range_header:
        headers["Range"] = range_header
    try:
        r = requests.get(target_url, headers=headers, stream=True, timeout=15)
        def generate():
            for chunk in r.iter_content(chunk_size=64 * 1024):
                if chunk:
                    yield chunk
        resp = Response(stream_with_context(generate()), status=r.status_code, mimetype=r.headers.get("Content-Type", "video/mp4"))
        resp.headers["Access-Control-Allow-Origin"] = "*"
        if "Content-Length" in r.headers:
            resp.headers["Content-Length"] = r.headers["Content-Length"]
        if "Content-Range" in r.headers:
            resp.headers["Content-Range"] = r.headers["Content-Range"]
        if "Accept-Ranges" in r.headers:
            resp.headers["Accept-Ranges"] = r.headers["Accept-Ranges"]
        return resp
    except Exception as e:
        return f"Proxy stream error: {e}", 502

# ---------------- LOCAL VIDEO UPLOAD & STREAMING ----------------

# LOCAL_DISK_FILES is initialized above

def stream_file_range(file_path: Path):
    if not file_path.exists() or not file_path.is_file():
        return "File not found", 404

    file_size = file_path.stat().st_size
    range_header = request.headers.get("Range", None)

    ext = file_path.suffix.lower()
    content_types = {
        ".mp4": "video/mp4",
        ".m4v": "video/mp4",
        ".webm": "video/webm",
        ".mkv": "video/webm",
        ".mov": "video/quicktime",
        ".avi": "video/x-msvideo",
        ".ogg": "video/ogg",
        ".ts": "video/mp2t"
    }
    content_type = content_types.get(ext, "video/mp4")

    if not range_header:
        def direct_stream():
            with open(file_path, "rb") as f:
                while True:
                    chunk = f.read(512 * 1024)
                    if not chunk:
                        break
                    yield chunk

        return Response(
            direct_stream(),
            mimetype=content_type,
            headers={
                "Content-Length": str(file_size),
                "Accept-Ranges": "bytes",
                "Access-Control-Allow-Origin": "*"
            }
        )

    m = re.match(r"bytes=(\d+)-(\d*)", range_header)
    if not m:
        return "Invalid Range", 416

    start = int(m.group(1))
    end = int(m.group(2)) if m.group(2) else file_size - 1
    if start >= file_size or end >= file_size or start > end:
        return "Range Not Satisfiable", 416

    chunk_length = (end - start) + 1

    def range_stream():
        try:
            with open(file_path, "rb") as f:
                f.seek(start)
                remaining = chunk_length
                while remaining > 0:
                    read_bytes = min(remaining, 512 * 1024)
                    data = f.read(read_bytes)
                    if not data:
                        break
                    remaining -= len(data)
                    yield data
        except (GeneratorExit, ConnectionResetError, BrokenPipeError):
            pass

    headers = {
        "Content-Range": f"bytes {start}-{end}/{file_size}",
        "Accept-Ranges": "bytes",
        "Content-Length": str(chunk_length),
        "Content-Type": content_type,
        "Access-Control-Allow-Origin": "*"
    }
    return Response(range_stream(), status=206, headers=headers)

@app.route("/stream_local/<filename>")
def stream_local_video(filename):
    file_path = UPLOAD_FOLDER / filename
    return stream_file_range(file_path)

def smart_find_disk_path(raw_path: str) -> Optional[Path]:
    raw_path = str(raw_path or "").strip().strip('"').strip("'")
    if not raw_path:
        return None

    # 1. Direct path check
    try:
        p = Path(raw_path).resolve()
        if p.exists() and p.is_file():
            return p
    except Exception:
        pass

    norm = raw_path.replace('/', '\\')
    # 2. Check for missing backslash in path (e.g. D:\HolosХолостяк.mp4 -> D:\Holos\Холостяк.mp4)
    for drive in ["D:\\", "C:\\", "E:\\", "F:\\", "d:\\", "c:\\", "e:\\", "f:\\"]:
        if norm.lower().startswith(drive.lower()):
            sub = norm[len(drive):]
            for i in range(1, len(sub)):
                cand_dir = Path(drive + sub[:i])
                if cand_dir.exists() and cand_dir.is_dir():
                    cand_file = cand_dir / sub[i:].lstrip('\\/')
                    if cand_file.exists() and cand_file.is_file():
                        return cand_file

    # 3. Extract filename from raw_path and search common locations
    m = re.search(r'([^\\/]+\.(mp4|mkv|webm|mov|m4v|avi|ts))$', raw_path, re.I)
    fname = m.group(1) if m else raw_path

    search_dirs = [
        Path("D:/"), Path("D:/Holos"), Path("D:/rave"),
        Path("E:/"), Path("C:/"), Path("F:/"),
        Path.home() / "Downloads",
        Path.home() / "Videos",
        Path.home() / "Desktop"
    ]
    for d in search_dirs:
        if not d.exists():
            continue
        cand = d / fname
        if cand.exists() and cand.is_file():
            return cand
        try:
            for sub in d.iterdir():
                if sub.is_dir() and not sub.name.startswith(('.', '$', 'Windows', 'Program')):
                    cand = sub / fname
                    if cand.exists() and cand.is_file():
                        return cand
        except Exception:
            pass

    return None

@app.route("/stream_disk/<token>")
def stream_disk_video(token):
    item = LOCAL_DISK_FILES.get(token) or state.get("disk_tokens", {}).get(token)
    if not item:
        for r in state.get("recent_disk_files", []):
            if r.get("token") == token or (r.get("path") and Path(r["path"]).exists()):
                item = r
                break
    if not item:
        return "Invalid stream token", 404
    file_path = Path(item["path"])
    return stream_file_range(file_path)

@app.route("/api/open_disk_path", methods=["POST"])
def api_open_disk_path():
    data = request.get_json(silent=True) or {}
    raw_path = str(data.get("path") or data.get("file_path") or data.get("filePath") or "").strip().strip('"').strip("'")
    if not raw_path:
        return jsonify({"error": "Путь к файлу не указан", "status": "error"}), 400

    try:
        p = smart_find_disk_path(raw_path)
        if not p or not p.exists() or not p.is_file():
            return jsonify({"error": f"Файл не найден на диске: {raw_path}", "status": "error"}), 404

        ext = p.suffix.lower()
        allowed_exts = [".mp4", ".mkv", ".webm", ".mov", ".m4v", ".avi", ".ts"]
        if ext not in allowed_exts:
            return jsonify({"error": f"Формат {ext} не поддерживается", "status": "error"}), 400

        token = uuid.uuid4().hex[:12]
        disk_info = {
            "path": str(p),
            "title": p.name,
            "size": p.stat().st_size,
            "token": token,
            "created_at": now()
        }
        LOCAL_DISK_FILES[token] = disk_info
        state.setdefault("disk_tokens", {})[token] = disk_info

        # Remember in persistent state
        recent = state.setdefault("recent_disk_files", [])
        recent = [r for r in recent if r.get("path") != str(p)]
        recent.insert(0, {
            "path": str(p),
            "filename": p.name,
            "title": p.name,
            "size": p.stat().st_size,
            "ts": now()
        })
        state["recent_disk_files"] = recent[:20]
        mark_dirty()

        return jsonify({
            "success": True,
            "status": "ok",
            "type": "mp4",
            "url": f"/stream_disk/{token}",
            "stream_url": f"/stream_disk/{token}",
            "title": p.name,
            "file_path": str(p),
            "size": p.stat().st_size
        })
    except Exception as e:
        return jsonify({"error": f"Ошибка доступа к файлу: {e}", "status": "error"}), 500

@app.route("/api/find_disk_file")
def api_find_disk_file():
    filename = clean_text(request.args.get("filename") or request.args.get("name") or "", 200).strip()
    if not filename:
        return jsonify({"found": False, "status": "error"})

    cand = smart_find_disk_path(filename)
    if cand and cand.exists() and cand.is_file():
        return jsonify({
            "success": True,
            "status": "ok",
            "found": True,
            "path": str(cand),
            "file_path": str(cand),
            "name": cand.name,
            "filename": cand.name,
            "size": cand.stat().st_size
        })

    return jsonify({"found": False, "status": "not_found"})

@app.route("/api/upload_chunk", methods=["POST"])
def api_upload_chunk():
    if "chunk" not in request.files:
        return jsonify({"error": "No chunk provided"}), 400

    upload_id = clean_text(request.form.get("upload_id"), 64)
    chunk_index = int(request.form.get("chunk_index", 0))
    total_chunks = int(request.form.get("total_chunks", 1))
    filename = clean_text(request.form.get("filename"), 120)

    if not upload_id or not filename:
        return jsonify({"error": "Invalid params"}), 400

    temp_dir = UPLOAD_FOLDER / f"part_{upload_id}"
    temp_dir.mkdir(parents=True, exist_ok=True)

    chunk_file = request.files["chunk"]
    chunk_path = temp_dir / f"chunk_{chunk_index:05d}"
    chunk_file.save(str(chunk_path))

    if chunk_index == total_chunks - 1:
        safe_name = re.sub(r'[^a-zA-Z0-9_.-]', '_', filename)
        final_filename = f"{upload_id[:8]}_{safe_name}"
        final_path = UPLOAD_FOLDER / final_filename

        with open(final_path, "wb") as outfile:
            for i in range(total_chunks):
                c_part = temp_dir / f"chunk_{i:05d}"
                if c_part.exists():
                    with open(c_part, "rb") as infile:
                        outfile.write(infile.read())
                    try:
                        c_part.unlink()
                    except OSError:
                        pass

        try:
            temp_dir.rmdir()
        except OSError:
            pass

        return jsonify({
            "complete": True,
            "status": "complete",
            "url": f"/stream_local/{final_filename}",
            "filename": final_filename,
            "title": filename,
            "size": final_path.stat().st_size
        })

    return jsonify({"complete": False, "chunk_index": chunk_index})

@app.route("/api/upload_video", methods=["POST"])
def api_upload_video():
    if "video" not in request.files:
        return jsonify({"error": "No video file provided"}), 400

    file = request.files["video"]
    if not file or not file.filename:
        return jsonify({"error": "Empty filename"}), 400

    filename = clean_text(file.filename, 120)
    ext = Path(filename).suffix.lower()
    allowed_exts = [".mp4", ".mkv", ".webm", ".mov", ".m4v", ".avi", ".ts"]
    if ext not in allowed_exts:
        return jsonify({"error": f"Формат {ext} не поддерживается"}), 400

    safe_name = re.sub(r'[^a-zA-Z0-9_.-]', '_', filename)
    unique_filename = f"{uuid.uuid4().hex[:8]}_{safe_name}"
    target_path = UPLOAD_FOLDER / unique_filename

    try:
        file.save(str(target_path))
        return jsonify({
            "success": True,
            "type": "mp4",
            "url": f"/stream_local/{unique_filename}",
            "title": filename,
            "size": target_path.stat().st_size
        })
    except Exception as e:
        return jsonify({"error": f"Upload failed: {e}"}), 500

@app.route("/api/local_videos")
@app.route("/api/local_files")
def api_local_videos():
    videos = []
    # 1. Uploaded videos
    try:
        for f in UPLOAD_FOLDER.iterdir():
            if f.is_file() and f.suffix.lower() in [".mp4", ".mkv", ".webm", ".mov", ".m4v", ".avi", ".ts"]:
                clean_t = re.sub(r'^[a-f0-9]{8}_', '', f.name)
                videos.append({
                    "filename": f.name,
                    "title": clean_t,
                    "url": f"/stream_local/{f.name}",
                    "stream_url": f"/stream_local/{f.name}",
                    "size": f.stat().st_size,
                    "created_at": f.stat().st_ctime,
                    "is_local_disk": False
                })
    except Exception:
        pass

    # 2. Recent disk files
    for r in state.get("recent_disk_files", []):
        p = Path(r.get("path", ""))
        if p.exists() and p.is_file():
            token = None
            for tok, item in LOCAL_DISK_FILES.items():
                if item.get("path") == str(p):
                    token = tok
                    break
            if not token:
                token = uuid.uuid4().hex[:12]
                LOCAL_DISK_FILES[token] = {
                    "path": str(p),
                    "title": p.name,
                    "size": p.stat().st_size,
                    "created_at": now()
                }
            videos.append({
                "filename": p.name,
                "title": f"📁 {p.name}",
                "path": str(p),
                "url": f"/stream_disk/{token}",
                "stream_url": f"/stream_disk/{token}",
                "size": p.stat().st_size,
                "created_at": r.get("ts", now()),
                "is_local_disk": True
            })

    videos.sort(key=lambda x: x["created_at"], reverse=True)
    return jsonify({"videos": videos, "files": videos})

@app.route("/api/delete_local_video", methods=["POST"])
def api_delete_local_video():
    data = request.get_json(silent=True) or {}
    filename = clean_text(data.get("filename"), 120)
    if not filename:
        return jsonify({"error": "No filename"}), 400

    target = UPLOAD_FOLDER / filename
    if target.exists() and target.is_file():
        try:
            target.unlink()
            return jsonify({"success": True})
        except OSError as e:
            return jsonify({"error": str(e)}), 500
    return jsonify({"error": "File not found"}), 404

# ---------------- SOCKET.IO REALTIME ENGINE ----------------

def bind_user_socket(user):
    if not user:
        return
    session = current_session()
    uid = str(user["id"])
    session["account_id"] = uid
    session["db_user_id"] = user["id"]
    session["user_name"] = user.get("display_name") or user.get("username")
    session["avatar"] = user.get("avatar") or ""
    try:
        join_room(f"user_{uid}")
    except Exception:
        pass
    database.update_user_status(user["id"], "online")

@socketio.on("connect")
def handle_connect():
    token = request.cookies.get("rave_token")
    if token:
        user = database.get_user_by_session(token)
        if user:
            bind_user_socket(user)
    emit_room_list()

@socketio.on("identify_user")
def handle_identify_user(data=None):
    token = request.cookies.get("rave_token")
    user = None
    if token:
        user = database.get_user_by_session(token)
    if not user and data and data.get("user_id"):
        user = database.get_user_by_id(data["user_id"])
    if user:
        bind_user_socket(user)
        emit("user_identified", {"success": True, "user_id": user["id"]})
        socketio.emit("friend_activity_update", {"type": "user_online", "user_id": user["id"]})

@socketio.on("disconnect")
def handle_disconnect():
    session = sessions.pop(request.sid, None)
    if session:
        uid = session.get("db_user_id") or session.get("account_id")
        if session.get("room_id"):
            room = state["rooms"].get(session["room_id"])
            if room:
                elect_room_leader(room)
                emit("room_members", {
                    "room_id": room["id"],
                    "members": room_members(room["id"]),
                    "online": room_online(room["id"])
                }, to=room_channel(room["id"]))
                emit("rooms_list", visible_rooms(), broadcast=True)
        if uid:
            still_online = any(
                str(s.get("db_user_id")) == str(uid) or str(s.get("account_id")) == str(uid)
                for s in sessions.values()
            )
            if not still_online:
                database.update_user_status(uid, "offline")
                socketio.emit("friend_activity_update", {"type": "user_offline", "user_id": uid})
            else:
                socketio.emit("friend_activity_update", {"type": "disconnect"})
        else:
            socketio.emit("friend_activity_update", {"type": "disconnect"})
    else:
        socketio.emit("friend_activity_update", {"type": "disconnect"})

@socketio.on("register_account")
def handle_register_account(data):
    nick = clean_text(data.get("nick"), 24) or "Гость"
    avatar = clean_text(data.get("avatar"), MAX_AVATAR_LEN)
    account_id = ensure_legacy_account(nick, avatar)
    account = state["accounts"][account_id]
    current_session()["account_id"] = account_id
    current_session()["user_name"] = account.get("nick") or nick
    current_session()["avatar"] = account.get("avatar") or avatar
    emit("account_registered", account)
    emit_room_list()

@socketio.on("update_profile")
def handle_update_profile(data):
    user = data.get("user") or {}
    acc_id = clean_text(user.get("id") or data.get("account_id"), 64) or current_session().get("account_id")
    name = clean_text(user.get("name") or user.get("username") or user.get("display_name") or data.get("name"), 50)
    avatar = clean_text(user.get("avatar") or data.get("avatar"), MAX_AVATAR_LEN)

    session = current_session()
    if acc_id:
        session["account_id"] = acc_id
    if name:
        session["user_name"] = name
    if avatar:
        session["avatar"] = avatar

    if acc_id:
        acc = state["accounts"].setdefault(acc_id, {"id": acc_id})
        if name:
            acc["nick"] = name
            acc["name"] = name
        if avatar:
            acc["avatar"] = avatar
        mark_dirty()

    room_id = session.get("room_id")
    if room_id:
        emit("room_members", {
            "room_id": room_id,
            "members": room_members(room_id),
            "online": room_online(room_id)
        }, to=room_channel(room_id))
        emit("room_members", {
            "room_id": room_id,
            "members": room_members(room_id),
            "online": room_online(room_id)
        }, broadcast=True)
    emit("rooms_list", visible_rooms(), broadcast=True)

@socketio.on("rooms_list")
def handle_rooms_list():
    emit_room_list()

@socketio.on("get_public_rooms")
def handle_get_public_rooms():
    emit("rooms_list", visible_rooms())

@socketio.on("ping_check")
def handle_ping_check(data):
    emit("pong_check", {
        "client_t": data.get("t") if isinstance(data, dict) else None,
        "server_time": now()
    })

@socketio.on("create_room")
def handle_create_room(data):
    user = data.get("user") or {}
    account_id = clean_text(user.get("id") or data.get("account_id"), 64) or current_session().get("account_id") or new_id("u_")
    user_name = clean_text(user.get("name") or user.get("username"), 50) or current_user_name() or "Зритель"
    avatar = clean_text(user.get("avatar"), MAX_AVATAR_LEN) or current_session().get("avatar", "")

    current_session()["account_id"] = account_id
    current_session()["user_name"] = user_name
    if avatar:
        current_session()["avatar"] = avatar

    name = clean_text(data.get("name") or data.get("title"), 40) or f"Комната {user_name}"
    private = bool(data.get("private", True)) if "private" in data else True
    code = clean_text(data.get("code"), 64)
    if private and not code:
        code = uuid.uuid4().hex[:6].upper()

    if len(state["rooms"]) >= MAX_ROOMS:
        emit("room_error", {"message": "Слишком много комнат на сервере"})
        return

    room_id, room = make_room(name=name, private=private, code=code, owner=account_id)
    room["leader_sid"] = request.sid
    state["rooms"][room_id] = room
    state["room_order"].append(room_id)
    mark_dirty()

    session = current_session()
    old_room_id = session.get("room_id")
    if old_room_id:
        leave_room(room_channel(old_room_id))
        old_room = state["rooms"].get(old_room_id)
        if old_room:
            elect_room_leader(old_room)
            emit("room_members", {
                "room_id": old_room_id,
                "members": room_members(old_room_id),
                "online": room_online(old_room_id)
            }, to=room_channel(old_room_id))
    session["room_id"] = room_id
    join_room(room_channel(room_id))

    emit("room_created", {"room": public_room(room), "code": code if private else ""})
    emit("room_joined", {"room": public_room(room), "code": code if private else "", "is_leader": True})
    emit_room_state(room, to_sid=request.sid)
    emit("rooms_list", visible_rooms(), broadcast=True)
    socketio.emit("friend_activity_update", {"room_id": room_id, "type": "created"})

@socketio.on("delete_room")
def handle_delete_room(data):
    room_id = clean_text(data.get("room_id"), 64)
    if not room_id or room_id == DEFAULT_ROOM_ID:
        emit("room_error", {"message": "Эту комнату нельзя удалить"})
        return

    room = state["rooms"].get(room_id)
    if not room:
        return

    session = current_session()
    account_id = session.get("account_id")
    if room.get("owner") and room.get("owner") != account_id and session.get("sid") != room.get("leader_sid"):
        emit("room_error", {"message": "Только создатель может удалить комнату"})
        return

    emit("room_closed", {"room_id": room_id, "message": "Комната закрыта создателем"}, to=room_channel(room_id))

    for sid, s in list(sessions.items()):
        if s.get("room_id") == room_id:
            s["room_id"] = DEFAULT_ROOM_ID
            try:
                leave_room(room_channel(room_id), sid=sid)
                join_room(room_channel(DEFAULT_ROOM_ID), sid=sid)
            except Exception:
                pass

    state["rooms"].pop(room_id, None)
    if room_id in state["room_order"]:
        state["room_order"].remove(room_id)
    mark_dirty()

    emit("rooms_list", visible_rooms(), broadcast=True)

@socketio.on("leave_room")
def handle_leave_room(data=None):
    session = current_session()
    room_id = session.get("room_id")
    if room_id:
        leave_room(room_channel(room_id))
        session["room_id"] = ""
        room = state["rooms"].get(room_id)
        if room:
            elect_room_leader(room)
            emit("room_members", {
                "room_id": room_id,
                "members": room_members(room_id),
                "online": room_online(room_id)
            }, to=room_channel(room_id))
        emit("room_left", {"room_id": room_id})
        emit("rooms_list", visible_rooms(), broadcast=True)
        socketio.emit("friend_activity_update", {"type": "leave", "room_id": room_id})

@socketio.on("join_room")
def handle_join_room(data):
    user = data.get("user") or {}
    account_id = clean_text(user.get("id") or data.get("account_id"), 64) or current_session().get("account_id") or new_id("u_")
    user_name = clean_text(user.get("name") or user.get("username") or data.get("name"), 50) or current_user_name() or "Зритель"
    user_avatar = clean_text(user.get("avatar") or data.get("avatar"), MAX_AVATAR_LEN) or current_session().get("avatar", "")

    room_id = clean_text(data.get("room_id"), 64)
    if not room_id:
        return
    code = clean_text(data.get("code"), 64)
    room = state["rooms"].get(room_id)
    if not room:
        room = {
            "id": room_id,
            "title": f"Кинозал {room_id}",
            "name": f"Кинозал {room_id}",
            "owner": account_id,
            "created_at": now(),
            "private": bool(code),
            "code": code,
            "video": default_video(),
            "chat": [],
            "members": [],
            "leader_sid": request.sid,
            **default_room_extras()
        }
        state["rooms"][room_id] = room
        if room_id not in state["room_order"]:
            state["room_order"].append(room_id)
        mark_dirty()

    if room.get("private"):
        is_owner = bool(account_id and str(account_id) == str(room.get("owner")))
        code_matches = bool(code and room.get("code") == code)
        is_friend = False
        if account_id and room.get("owner"):
            try:
                is_friend = bool(database.are_friends(account_id, room.get("owner")))
            except Exception:
                is_friend = False
        if not (is_owner or code_matches or is_friend):
            emit("room_error", {"message": "Комната приватная. Доступ разрешён только друзьям или по секретному коду"})
            return

    session = current_session()
    old_room_id = session.get("room_id")
    if old_room_id and old_room_id != room_id:
        leave_room(room_channel(old_room_id))
        old_room = state["rooms"].get(old_room_id)
        if old_room:
            elect_room_leader(old_room)
            emit("room_members", {
                "room_id": old_room_id,
                "members": room_members(old_room_id),
                "online": room_online(old_room_id)
            }, to=room_channel(old_room_id))
    session["account_id"] = account_id
    session["user_name"] = user_name
    session["avatar"] = user_avatar
    session["room_id"] = room_id
    join_room(room_channel(room_id))
    elect_room_leader(room)

    if account_id:
        acc = state["accounts"].setdefault(account_id, {"id": account_id})
        acc["nick"] = user_name
        acc["name"] = user_name
        if user_avatar:
            acc["avatar"] = user_avatar
        mark_dirty()

    room["last_active"] = now()
    room_code = room.get("code", "") if (room.get("private") and (is_owner or is_friend or code_matches)) else ""
    emit("room_joined", {
        "room": public_room(room),
        "code": room_code,
        "is_leader": (request.sid == room.get("leader_sid"))
    })
    socketio.emit("friend_activity_update", {"room_id": room_id, "type": "joined"})
    emit_room_state(room, to_sid=request.sid)
    emit("room_members", {
        "room_id": room_id,
        "members": room_members(room_id),
        "online": room_online(room_id)
    }, to=room_channel(room_id))
    emit("room_members", {
        "room_id": room_id,
        "members": room_members(room_id),
        "online": room_online(room_id)
    }, broadcast=True)
    emit("room_online", {"room_id": room_id, "online": room_online(room_id)}, to=room_channel(room_id))
    emit("rooms_list", visible_rooms(), broadcast=True)

@socketio.on("send_reaction")
def handle_send_reaction(data):
    requested_room_id = clean_text(data.get("room_id") or "", 64)
    if requested_room_id and requested_room_id in state["rooms"]:
        target_room_id = requested_room_id
    else:
        room = current_room()
        if not room:
            return
        target_room_id = room["id"]

    emoji = clean_text(data.get("emoji") or "", 8).strip()
    if not emoji:
        return

    user = data.get("user") or {}
    user_name = clean_text(user.get("name") or user.get("username") or data.get("author") or current_user_name(), 50)

    # Broadcast reaction to all users in room
    emit("room_reaction", {
        "room_id": target_room_id,
        "emoji": emoji,
        "author": user_name
    }, to=room_channel(target_room_id))

@socketio.on("send_message")
@socketio.on("send_chat")
def handle_send_message(data):
    requested_room_id = clean_text(data.get("room_id") or "", 64)
    session = current_session()
    if requested_room_id and requested_room_id in state["rooms"]:
        room = state["rooms"][requested_room_id]
        session["room_id"] = requested_room_id
        join_room(room_channel(requested_room_id))
    else:
        room = current_room()
        if not room:
            return

    user = data.get("user") or {}
    account_id = clean_text(user.get("id") or user.get("account_id") or data.get("account_id"), 64) or current_session().get("account_id")
    user_name = clean_text(user.get("name") or user.get("username") or data.get("author") or data.get("sender_name"), 50) or current_user_name()
    user_avatar = clean_text(user.get("avatar") or data.get("avatar") or data.get("sender_avatar"), MAX_AVATAR_LEN) or current_session().get("avatar", "")
    text = clean_text(data.get("text") or data.get("message"), 1000)
    if not text:
        return

    msg = {
        "id": new_id("m_"),
        "kind": "message",
        "account_id": account_id,
        "author": user_name,
        "name": user_name,
        "avatar": user_avatar,
        "sender_name": user_name,
        "sender_avatar": user_avatar,
        "text": text,
        "ts": now(),
        "reactions": {},
    }
    remember_message(room, msg)
    emit("chat_message", msg, to=room_channel(room["id"]))
    emit("new_message", msg, to=room_channel(room["id"]))
    emit("receive_message", msg, to=room_channel(room["id"]))

@socketio.on("send_media")
def handle_send_media(data):
    requested_room_id = clean_text(data.get("room_id") or "", 64)
    session = current_session()
    if requested_room_id and requested_room_id in state["rooms"]:
        room = state["rooms"][requested_room_id]
        session["room_id"] = requested_room_id
        join_room(room_channel(requested_room_id))
    else:
        room = current_room()
        if not room:
            return

    user = data.get("user") or {}
    account_id = clean_text(user.get("id") or user.get("account_id") or data.get("account_id"), 64) or current_session().get("account_id")
    user_name = clean_text(user.get("name") or user.get("username") or data.get("author") or data.get("sender_name"), 50) or current_user_name()
    user_avatar = clean_text(user.get("avatar") or data.get("avatar") or data.get("sender_avatar"), MAX_AVATAR_LEN) or current_session().get("avatar", "")
    src = clean_text(data.get("src") or data.get("url"), MAX_MEDIA_LEN)
    if not src:
        return

    msg = {
        "id": new_id("m_"),
        "kind": "media",
        "account_id": account_id,
        "author": user_name,
        "name": user_name,
        "avatar": user_avatar,
        "sender_name": user_name,
        "sender_avatar": user_avatar,
        "src": src,
        "ts": now(),
        "reactions": {},
    }
    remember_message(room, msg)
    emit("chat_message", msg, to=room_channel(room["id"]))
    emit("new_message", msg, to=room_channel(room["id"]))
    emit("receive_message", msg, to=room_channel(room["id"]))

@socketio.on("message_reaction")
def handle_message_reaction(data):
    room = current_room()
    if not room:
        return
    msg_id = clean_text(data.get("message_id") or data.get("id"), 64)
    emoji = clean_text(data.get("emoji") or data.get("reaction"), 8)
    if emoji not in ALLOWED_REACTIONS or not msg_id:
        return

    acc_id = current_session().get("account_id") or request.sid
    for msg in room.get("chat", []):
        if msg.get("id") == msg_id:
            reactions = msg.setdefault("reactions", {})
            users = reactions.setdefault(emoji, [])
            if acc_id in users:
                users.remove(acc_id)
                if not users:
                    reactions.pop(emoji, None)
            else:
                users.append(acc_id)
            mark_dirty()
            emit("message_reactions", {"message_id": msg_id, "reactions": reactions}, to=room_channel(room["id"]))
            break

@socketio.on("typing_start")
def handle_typing_start():
    room = current_room()
    if room:
        emit("user_typing", {"user_name": current_user_name(), "sid": request.sid}, to=room_channel(room["id"]), include_self=False)

@socketio.on("typing_stop")
def handle_typing_stop():
    room = current_room()
    if room:
        emit("user_stopped_typing", {"sid": request.sid}, to=room_channel(room["id"]), include_self=False)

@socketio.on("change_audio")
def handle_change_audio(data):
    room = require_room()
    if not room:
        return
    try:
        index = int(data.get("audio_index", 0))
    except (ValueError, TypeError):
        index = 0
    video = room["video"]
    video["selected_audio"] = index
    mark_dirty()
    emit("audio_track_changed", {
        "selected_audio": index,
        "source_name": current_user_name()
    }, to=room_channel(room["id"]))

def set_room_video(room: Dict[str, Any], raw_url: str, title: str = "", poster: str = "", video_type: Optional[str] = None, duration: float = 0.0, source_sid: str = "", source_name: str = "", audio_tracks: Optional[list] = None, subtitles: Optional[list] = None, kp_id: str = "", imdb_id: str = "", season: Any = None, episode: Any = None, selected_audio: int = 0):
    media_data = VideoResolver.resolve(raw_url)
    video = room["video"]
    chosen_title = clean_text(title, 120) or media_data.get("title") or "Без названия"
    v_type = video_type or media_data.get("type")
    if v_type in ("none", "", None):
        v_type = "direct"
    
    sid = source_sid or (request.sid if request else "")
    uname = source_name or current_user_name()

    video.update({
        "url": media_data.get("url") or raw_url,
        "type": v_type,
        "id": media_data.get("id") or new_id("v_"),
        "title": chosen_title,
        "poster": media_data.get("poster") or clean_text(poster, 500) or "",
        "duration": float(duration or media_data.get("duration") or 0.0),
        "playing": True,
        "time": 0.0,
        "updated_at": now(),
        "seq": video.get("seq", 0) + 1,
        "source_sid": sid,
        "source_name": uname,
        "audio_tracks": audio_tracks or media_data.get("audio_tracks") or [],
        "subtitles": subtitles or media_data.get("subtitles") or [],
        "selected_audio": int(selected_audio or 0),
        "kp_id": kp_id or media_data.get("kp_id", ""),
        "imdb_id": imdb_id or media_data.get("imdb_id", ""),
        "season": season,
        "episode": episode,
    })

    remember_video(room, video)
    mark_dirty()

    current_vid = current_video(room)
    payload = {
        **current_vid,
        "video": current_vid,
        "room_id": room["id"],
        "action": "play",
        "server_time": now(),
        "source_sid": sid,
        "source_name": uname,
    }
    emit("video_changed", payload, to=room_channel(room["id"]), include_self=True)
    emit("video_state", payload, to=room_channel(room["id"]), include_self=True)
    emit("video_play", {
        "room_id": room["id"],
        "action": "play",
        "time": 0.0,
        "playing": True,
        "server_time": now(),
        "seq": video["seq"],
        "source_sid": sid,
        "source_name": uname,
    }, to=room_channel(room["id"]), include_self=True)
    emit("room_history", room.get("history", [])[-MAX_HISTORY_LINKS:], to=room_channel(room["id"]))
    emit("rooms_list", visible_rooms(), broadcast=True)
    socketio.emit("friend_activity_update", {"room_id": room["id"], "type": "video_changed"})

@socketio.on("change_video")
def handle_change_video(data):
    requested_room_id = clean_text(data.get("room_id") or "", 64)
    session = current_session()
    if requested_room_id and requested_room_id in state["rooms"]:
        if session.get("room_id") and session["room_id"] != requested_room_id:
            try:
                leave_room(room_channel(session["room_id"]))
            except Exception:
                pass
        room = state["rooms"][requested_room_id]
        session["room_id"] = requested_room_id
        try:
            join_room(room_channel(requested_room_id))
        except Exception:
            pass
    else:
        room = current_room()
        if not room:
            emit("room_error", {"message": "Сначала войдите в комнату для смены видео"})
            return

    raw_url = str(data.get("url") or "").strip()
    set_room_video(room, raw_url,
                   title=data.get("title", ""),
                   poster=data.get("poster", ""),
                   video_type=data.get("type"),
                   duration=float(data.get("duration") or 0.0),
                   audio_tracks=data.get("audio_tracks"),
                   subtitles=data.get("subtitles"),
                   kp_id=str(data.get("kp_id") or ""),
                   imdb_id=str(data.get("imdb_id") or ""),
                   season=data.get("season"),
                   episode=data.get("episode"),
                   selected_audio=int(data.get("selected_audio") or 0))

# ================================= VIDEO QUEUE EVENTS =================================

@socketio.on("queue_add")
def handle_queue_add(data):
    if not isinstance(data, dict):
        return
    room_id = clean_text(data.get("room_id") or "", 64)
    room = state["rooms"].get(room_id) or current_room()
    if not room:
        emit("room_error", {"message": "Комната не найдена"})
        return
    raw_url = str(data.get("url") or "").strip()
    if not raw_url:
        return
    media_data = VideoResolver.resolve(raw_url)
    item = {
        "id": new_id("q_"),
        "url": media_data.get("url") or raw_url,
        "raw_url": raw_url,
        "type": media_data.get("type") if media_data.get("type") not in ("none", "", None) else (data.get("type") or "direct"),
        "title": clean_text(data.get("title"), 120) or media_data.get("title") or "Видео из очереди",
        "poster": media_data.get("poster") or clean_text(data.get("poster"), 500) or "",
        "duration": float(media_data.get("duration") or data.get("duration") or 0.0),
        "added_by": current_user_name(),
        "added_at": now(),
    }
    q = room.setdefault("queue", [])
    q.append(item)
    mark_dirty()
    emit("queue_updated", {"room_id": room["id"], "queue": q}, to=room_channel(room["id"]))

@socketio.on("queue_remove")
def handle_queue_remove(data):
    if not isinstance(data, dict):
        return
    room_id = clean_text(data.get("room_id") or "", 64)
    room = state["rooms"].get(room_id) or current_room()
    if not room:
        return
    item_id = clean_text(data.get("item_id") or "", 64)
    q = room.setdefault("queue", [])
    room["queue"] = [item for item in q if item.get("id") != item_id]
    mark_dirty()
    emit("queue_updated", {"room_id": room["id"], "queue": room["queue"]}, to=room_channel(room["id"]))

@socketio.on("queue_reorder")
def handle_queue_reorder(data):
    if not isinstance(data, dict):
        return
    room_id = clean_text(data.get("room_id") or "", 64)
    room = state["rooms"].get(room_id) or current_room()
    if not room:
        return
    try:
        from_idx = int(data.get("from_index"))
        to_idx = int(data.get("to_index"))
    except (TypeError, ValueError):
        return
    q = room.setdefault("queue", [])
    if 0 <= from_idx < len(q) and 0 <= to_idx < len(q):
        item = q.pop(from_idx)
        q.insert(to_idx, item)
        mark_dirty()
        emit("queue_updated", {"room_id": room["id"], "queue": q}, to=room_channel(room["id"]))

@socketio.on("queue_play_next")
def handle_queue_play_next(data=None):
    data = data or {}
    room_id = clean_text(data.get("room_id") or "", 64)
    room = state["rooms"].get(room_id) or current_room()
    if not room:
        return
    q = room.setdefault("queue", [])
    if not q:
        return
    next_item = q.pop(0)
    mark_dirty()
    set_room_video(room, next_item.get("raw_url") or next_item.get("url"),
                   title=next_item.get("title", ""),
                   poster=next_item.get("poster", ""),
                   video_type=next_item.get("type"),
                   duration=next_item.get("duration", 0.0))
    emit("queue_updated", {"room_id": room["id"], "queue": q}, to=room_channel(room["id"]))

@socketio.on("queue_play_item")
def handle_queue_play_item(data):
    if not isinstance(data, dict):
        return
    room_id = clean_text(data.get("room_id") or "", 64)
    room = state["rooms"].get(room_id) or current_room()
    if not room:
        return
    item_id = clean_text(data.get("item_id") or "", 64)
    q = room.setdefault("queue", [])
    target = None
    new_q = []
    for it in q:
        if it.get("id") == item_id and target is None:
            target = it
        else:
            new_q.append(it)
    if target:
        room["queue"] = new_q
        mark_dirty()
        set_room_video(room, target.get("raw_url") or target.get("url"),
                       title=target.get("title", ""),
                       poster=target.get("poster", ""),
                       video_type=target.get("type"),
                       duration=target.get("duration", 0.0))
        emit("queue_updated", {"room_id": room["id"], "queue": new_q}, to=room_channel(room["id"]))

@socketio.on("queue_clear")
def handle_queue_clear(data=None):
    data = data or {}
    room_id = clean_text(data.get("room_id") or "", 64)
    room = state["rooms"].get(room_id) or current_room()
    if not room:
        return
    room["queue"] = []
    mark_dirty()
    emit("queue_updated", {"room_id": room["id"], "queue": []}, to=room_channel(room["id"]))

@socketio.on("save_moment")
def handle_save_moment(data):
    room = require_room()
    if not room:
        return
    video = current_video(room)
    try:
        t = max(0.0, float(data.get("time", video.get("time", 0.0))))
    except (TypeError, ValueError):
        t = 0.0
    item = {
        "id": new_id("mark_"),
        "time": t,
        "url": clean_text(video.get("url"), 2000),
        "type": clean_text(video.get("type"), 16),
        "video_id": clean_text(video.get("id"), 64),
        "title": clean_text(video.get("title"), 120),
        "account_id": current_session().get("account_id"),
        "label": clean_text(data.get("label"), 80) or f"Момент {int(t//60)}:{int(t%60):02d}",
        "ts": now(),
    }
    room.setdefault("moments", []).insert(0, item)
    room["moments"] = room["moments"][:MAX_MOMENTS]
    mark_dirty()
    emit("moments_list", room["moments"], to=room_channel(room["id"]))
    emit("room_moments", {"room_id": room["id"], "moments": room["moments"]}, to=room_channel(room["id"]))

@socketio.on("video_play")
def handle_video_play(data):
    update_video_state("play", data)

@socketio.on("video_pause")
def handle_video_pause(data):
    update_video_state("pause", data)

@socketio.on("video_seek")
def handle_video_seek(data):
    update_video_state("seek", data)

@socketio.on("video_heartbeat")
def handle_video_heartbeat(data):
    room = require_room(data if isinstance(data, dict) else None)
    if not room:
        return
    # Only room leader or owner can update heartbeat clock
    if room.get("leader_sid") and request.sid != room.get("leader_sid"):
        return
    video = room["video"]
    if video.get("playing"):
        try:
            t = float(data.get("time", 0.0))
            video["time"] = max(0.0, t)
            video["updated_at"] = now()
            mark_dirty()
        except (TypeError, ValueError):
            pass

@socketio.on("client_buffer_status")
def handle_client_buffer_status(data):
    room = current_room()
    if not room:
        return
    is_buffering = bool(data.get("is_buffering", False))
    session = current_session()
    session["is_buffering"] = is_buffering
    emit("user_buffer_status", {
        "sid": request.sid,
        "account_id": session.get("account_id"),
        "user_name": current_user_name(),
        "is_buffering": is_buffering
    }, to=room_channel(room["id"]), include_self=False)
    emit("room_members", {
        "room_id": room["id"],
        "members": room_members(room["id"]),
        "online": room_online(room["id"])
    }, to=room_channel(room["id"]))

@socketio.on("send_reaction")
def handle_send_reaction(data):
    room = current_room()
    if not room:
        return
    emoji = clean_text(data.get("emoji") or data.get("text"), 8)
    if emoji not in ALLOWED_REACTIONS:
        return
    emit("float_reaction", {
        "emoji": emoji,
        "sid": request.sid,
        "user_name": current_user_name(),
        "avatar": current_session().get("avatar", "")
    }, to=room_channel(room["id"]))

def update_video_state(action: str, data: Dict[str, Any]):
    room = require_room(data)
    if not room:
        return
    try:
        t = max(0.0, float(data.get("time", 0.0)))
    except (TypeError, ValueError):
        t = 0.0

    video = room["video"]
    seq = video.get("seq", 0) + 1
    video["seq"] = seq
    video["time"] = t
    video["updated_at"] = now()
    video["source_sid"] = request.sid
    user_name = current_user_name()
    video["source_name"] = user_name

    if action == "play":
        video["playing"] = True
    elif action == "pause":
        video["playing"] = False
    elif action == "seek":
        pass

    mark_dirty()

    payload = {
        "room_id": room["id"],
        "action": action,
        "time": t,
        "playing": video["playing"],
        "server_time": now(),
        "seq": seq,
        "source_sid": request.sid,
        "source_name": user_name,
    }
    emit(f"video_{action}", payload, to=room_channel(room["id"]), include_self=True)
    emit("video_ack", payload)

@socketio.on("request_sync")
def handle_request_sync(data=None):
    room = require_room(data if isinstance(data, dict) else None)
    if room:
        emit("current_state", {
            **current_video(room),
            "room_id": room["id"],
            "server_time": now(),
            "is_leader": (request.sid == room.get("leader_sid"))
        })

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5050))
    socketio.run(app, host="0.0.0.0", port=port, debug=False)
