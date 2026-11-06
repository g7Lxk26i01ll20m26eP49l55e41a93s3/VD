import sqlite3
import os
import time
import uuid
import json
from pathlib import Path
from typing import Dict, Any, Optional, List
from werkzeug.security import generate_password_hash, check_password_hash

DB_PATH = Path(__file__).resolve().parent / "rave.db"
BACKUP_PATH = Path(__file__).resolve().parent / "users_backup.json"

def backup_database_to_json():
    """Backs up all users, stats, friends and watch history to users_backup.json."""
    try:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, username, display_name, password_hash, avatar, banner_color, bio, role, status, created_at, last_seen FROM users")
            users = [dict(r) for r in cursor.fetchall()]

            cursor.execute("SELECT * FROM user_stats")
            stats = [dict(r) for r in cursor.fetchall()]

            cursor.execute("SELECT user_id, friend_id, status, created_at FROM friends")
            friends = [dict(r) for r in cursor.fetchall()]

            cursor.execute("SELECT user_id, title, poster, url, media_type, duration_sec, watched_sec, updated_at FROM watch_history")
            history = [dict(r) for r in cursor.fetchall()]

        data = {
            "version": 2,
            "updated_at": time.time(),
            "users": users,
            "user_stats": stats,
            "friends": friends,
            "watch_history": history
        }
        temp_path = BACKUP_PATH.with_suffix(".tmp")
        temp_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        temp_path.replace(BACKUP_PATH)
    except Exception as e:
        print(f"[DB] Backup warning: {e}")

def restore_database_from_json():
    """Restores database from users_backup.json if database is empty."""
    if not BACKUP_PATH.exists():
        return
    try:
        data = json.loads(BACKUP_PATH.read_text(encoding="utf-8"))
        users = data.get("users", [])
        if not users:
            return

        with get_connection() as conn:
            cursor = conn.cursor()
            for u in users:
                cursor.execute("""
                INSERT OR IGNORE INTO users (id, username, display_name, password_hash, avatar, banner_color, bio, role, status, created_at, last_seen)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    u.get("id"),
                    u.get("username"),
                    u.get("display_name", u.get("username")),
                    u.get("password_hash"),
                    u.get("avatar", ""),
                    u.get("banner_color", "#8b5cf6"),
                    u.get("bio", "Смотрю фильмы и сериалы с друзьями в VD 🍿"),
                    u.get("role", "user"),
                    u.get("status", "offline"),
                    u.get("created_at", time.time()),
                    u.get("last_seen", time.time())
                ))

            for s in data.get("user_stats", []):
                cursor.execute("""
                INSERT OR IGNORE INTO user_stats (
                    user_id, total_watch_seconds, movies_count, rooms_created, messages_sent,
                    day_mon_sec, day_tue_sec, day_wed_sec, day_thu_sec, day_fri_sec, day_sat_sec, day_sun_sec, last_activity_day
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    s.get("user_id"),
                    s.get("total_watch_seconds", 0),
                    s.get("movies_count", 0),
                    s.get("rooms_created", 0),
                    s.get("messages_sent", 0),
                    s.get("day_mon_sec", 0),
                    s.get("day_tue_sec", 0),
                    s.get("day_wed_sec", 0),
                    s.get("day_thu_sec", 0),
                    s.get("day_fri_sec", 0),
                    s.get("day_sat_sec", 0),
                    s.get("day_sun_sec", 0),
                    s.get("last_activity_day", 0)
                ))

            for f in data.get("friends", []):
                cursor.execute("""
                INSERT OR IGNORE INTO friends (user_id, friend_id, status, created_at)
                VALUES (?, ?, ?, ?)
                """, (
                    f.get("user_id"),
                    f.get("friend_id"),
                    f.get("status", "accepted"),
                    f.get("created_at", time.time())
                ))

            for h in data.get("watch_history", []):
                cursor.execute("""
                INSERT OR IGNORE INTO watch_history (user_id, title, poster, url, media_type, duration_sec, watched_sec, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    h.get("user_id"),
                    h.get("title"),
                    h.get("poster", ""),
                    h.get("url", ""),
                    h.get("media_type", "movie"),
                    h.get("duration_sec", 0),
                    h.get("watched_sec", 0),
                    h.get("updated_at", time.time())
                ))

            conn.commit()
            print(f"[DB] Successfully restored {len(users)} users from backup!")
    except Exception as e:
        print(f"[DB] Restore warning: {e}")

def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH), timeout=15.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    return conn

def init_db():
    """Initializes the database schema with users, stats, history and session tables."""
    with get_connection() as conn:
        cursor = conn.cursor()

        # 1. Users Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL COLLATE NOCASE,
            display_name TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            avatar TEXT DEFAULT '',
            banner_color TEXT DEFAULT '#8b5cf6',
            bio TEXT DEFAULT 'Смотрю фильмы и сериалы с друзьями в VD 🍿',
            role TEXT DEFAULT 'user',
            status TEXT DEFAULT 'online',
            created_at REAL NOT NULL,
            last_seen REAL NOT NULL
        );
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);")

        # 2. User Stats Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_stats (
            user_id INTEGER PRIMARY KEY,
            total_watch_seconds INTEGER DEFAULT 0,
            movies_count INTEGER DEFAULT 0,
            rooms_created INTEGER DEFAULT 0,
            messages_sent INTEGER DEFAULT 0,
            day_mon_sec INTEGER DEFAULT 0,
            day_tue_sec INTEGER DEFAULT 0,
            day_wed_sec INTEGER DEFAULT 0,
            day_thu_sec INTEGER DEFAULT 0,
            day_fri_sec INTEGER DEFAULT 0,
            day_sat_sec INTEGER DEFAULT 0,
            day_sun_sec INTEGER DEFAULT 0,
            last_activity_day INTEGER DEFAULT 0,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );
        """)

        # 3. Watch History Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS watch_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            poster TEXT DEFAULT '',
            url TEXT DEFAULT '',
            media_type TEXT DEFAULT 'movie',
            duration_sec INTEGER DEFAULT 0,
            watched_sec INTEGER DEFAULT 0,
            updated_at REAL NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_watch_history_user ON watch_history(user_id, updated_at DESC);")

        # 4. Auth Sessions Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS auth_sessions (
            token TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL,
            created_at REAL NOT NULL,
            expires_at REAL NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        );
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_sessions_user ON auth_sessions(user_id);")

        # 5. Friends & Duo Connections Table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS friends (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            friend_id INTEGER NOT NULL,
            status TEXT DEFAULT 'accepted',
            created_at REAL NOT NULL,
            UNIQUE(user_id, friend_id),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (friend_id) REFERENCES users(id) ON DELETE CASCADE
        );
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_friends_user ON friends(user_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_friends_friend ON friends(friend_id);")

        conn.commit()
        cursor.execute("SELECT count(*) FROM users")
        row = cursor.fetchone()
        count = row[0] if row else 0
        if count == 0:
            restore_database_from_json()
        else:
            backup_database_to_json()

# ================================= USER REPOSITORY =================================

def create_user(username: str, display_name: str, password: str, avatar: str = "") -> Dict[str, Any]:
    username = username.strip().lower()
    display_name = display_name.strip() or username
    if len(username) < 3 or len(username) > 24:
        raise ValueError("Имя пользователя должно быть от 3 до 24 символов")
    if not username.replace("_", "").isalnum():
        raise ValueError("Имя пользователя может содержать только латинские буквы, цифры и _")
    if len(password) < 4:
        raise ValueError("Пароль должен содержать минимум 4 символа")

    now_ts = time.time()
    pwd_hash = generate_password_hash(password)

    default_avatars = [
        "https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=150&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=150&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1517841905240-472988babdf9?w=150&auto=format&fit=crop&q=80",
        "https://images.unsplash.com/photo-1539571696357-5a69c17a67c6?w=150&auto=format&fit=crop&q=80"
    ]
    if not avatar:
        avatar = default_avatars[len(username) % len(default_avatars)]

    with get_connection() as conn:
        cursor = conn.cursor()
        try:
            cursor.execute("""
            INSERT INTO users (username, display_name, password_hash, avatar, created_at, last_seen)
            VALUES (?, ?, ?, ?, ?, ?)
            """, (username, display_name, pwd_hash, avatar, now_ts, now_ts))
            user_id = cursor.lastrowid

            # Initialize stats
            cursor.execute("""
            INSERT INTO user_stats (user_id, total_watch_seconds)
            VALUES (?, 0)
            """, (user_id,))

            conn.commit()
            backup_database_to_json()
            return get_user_by_id(user_id)
        except sqlite3.IntegrityError:
            raise ValueError(f"Пользователь @{username} уже существует")

def authenticate_user(username: str, password: str) -> Optional[Dict[str, Any]]:
    username = username.strip().lower()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        row = cursor.fetchone()
        if not row:
            return None
        if not check_password_hash(row["password_hash"], password):
            return None

        # Update last seen
        cursor.execute("UPDATE users SET last_seen = ? WHERE id = ?", (time.time(), row["id"]))
        conn.commit()
        return dict(row)

def get_user_by_id(user_id: int) -> Optional[Dict[str, Any]]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, username, display_name, avatar, banner_color, bio, role, status, created_at, last_seen FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()
        return dict(row) if row else None

def get_user_by_username(username: str) -> Optional[Dict[str, Any]]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, username, display_name, avatar, banner_color, bio, role, status, created_at, last_seen FROM users WHERE username = ?", (username.strip().lower(),))
        row = cursor.fetchone()
        return dict(row) if row else None

def update_user_profile(user_id: int, display_name: Optional[str] = None, bio: Optional[str] = None, avatar: Optional[str] = None, banner_color: Optional[str] = None, status: Optional[str] = None) -> Dict[str, Any]:
    fields = []
    values = []
    if display_name is not None and display_name.strip():
        fields.append("display_name = ?")
        values.append(display_name.strip()[:60])
    if bio is not None:
        fields.append("bio = ?")
        values.append(bio.strip()[:300])
    if avatar is not None and avatar.strip():
        fields.append("avatar = ?")
        values.append(avatar.strip())
    if banner_color is not None and banner_color.strip():
        fields.append("banner_color = ?")
        values.append(banner_color.strip()[:120])
    if status is not None:
        fields.append("status = ?")
        values.append(status.strip()[:60])

    if not fields:
        return get_user_by_id(user_id)

    values.append(user_id)
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(f"UPDATE users SET {', '.join(fields)} WHERE id = ?", values)
        conn.commit()
        backup_database_to_json()

    return get_user_by_id(user_id)

# ================================= SESSIONS =================================

def create_session(user_id: int, duration_days: int = 30) -> str:
    token = uuid.uuid4().hex + uuid.uuid4().hex
    now_ts = time.time()
    expires_ts = now_ts + (duration_days * 86400)

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        INSERT INTO auth_sessions (token, user_id, created_at, expires_at)
        VALUES (?, ?, ?, ?)
        """, (token, user_id, now_ts, expires_ts))
        conn.commit()

    return token

def get_user_by_session(token: str) -> Optional[Dict[str, Any]]:
    if not token or not isinstance(token, str):
        return None
    now_ts = time.time()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        SELECT u.id, u.username, u.display_name, u.avatar, u.banner_color, u.bio, u.role, u.status, u.created_at, u.last_seen
        FROM auth_sessions s
        JOIN users u ON s.user_id = u.id
        WHERE s.token = ? AND s.expires_at > ?
        """, (token.strip(), now_ts))
        row = cursor.fetchone()
        if not row:
            return None
        
        # Periodically bump last_seen
        cursor.execute("UPDATE users SET last_seen = ? WHERE id = ?", (now_ts, row["id"]))
        conn.commit()
        return dict(row)

def delete_session(token: str):
    if not token:
        return
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM auth_sessions WHERE token = ?", (token.strip(),))
        conn.commit()

# ================================= STATS & WATCH TIME ENGINE =================================

def record_watch_time(user_id: int, seconds_delta: int, video_title: str = "", video_poster: str = "", video_url: str = "", media_type: str = "movie", duration: int = 0) -> Dict[str, Any]:
    """Records real watch time with anti-fraud clamping (max 30s credited per call)."""
    delta = max(1, min(int(seconds_delta or 15), 30))
    now_ts = time.time()
    current_day = time.localtime(now_ts).tm_wday  # 0 is Mon, 6 is Sun

    day_col_map = {
        0: "day_mon_sec",
        1: "day_tue_sec",
        2: "day_wed_sec",
        3: "day_thu_sec",
        4: "day_fri_sec",
        5: "day_sat_sec",
        6: "day_sun_sec"
    }
    col_name = day_col_map.get(current_day, "day_mon_sec")

    with get_connection() as conn:
        cursor = conn.cursor()
        # 1. Update cumulative stats & weekly distribution
        cursor.execute(f"""
        UPDATE user_stats
        SET total_watch_seconds = total_watch_seconds + ?,
            {col_name} = {col_name} + ?,
            last_activity_day = ?
        WHERE user_id = ?
        """, (delta, delta, current_day, user_id))

        # 2. Update watch history if title provided
        if video_title and video_title.strip():
            clean_title = video_title.strip()[:150]
            cursor.execute("""
            SELECT id, watched_sec FROM watch_history
            WHERE user_id = ? AND title = ?
            LIMIT 1
            """, (user_id, clean_title))
            row = cursor.fetchone()
            if row:
                cursor.execute("""
                UPDATE watch_history
                SET watched_sec = watched_sec + ?,
                    updated_at = ?,
                    poster = CASE WHEN ? != '' THEN ? ELSE poster END,
                    url = CASE WHEN ? != '' THEN ? ELSE url END
                WHERE id = ?
                """, (delta, now_ts, video_poster, video_poster, video_url, video_url, row["id"]))
            else:
                cursor.execute("""
                INSERT INTO watch_history (user_id, title, poster, url, media_type, duration_sec, watched_sec, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (user_id, clean_title, video_poster, video_url, media_type, duration, delta, now_ts))

                # Increment unique movies watched count
                cursor.execute("UPDATE user_stats SET movies_count = movies_count + 1 WHERE user_id = ?", (user_id,))

        conn.commit()

    return get_user_stats(user_id)

def get_user_stats(user_id: int) -> Dict[str, Any]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM user_stats WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        if not row:
            cursor.execute("INSERT OR IGNORE INTO user_stats (user_id) VALUES (?)", (user_id,))
            conn.commit()
            cursor.execute("SELECT * FROM user_stats WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()

        stats = dict(row) if row else {}
        total_sec = stats.get("total_watch_seconds", 0)

        # Compute level and badges
        level = 1 + (total_sec // 7200) # 1 level per 2 hours
        hours = round(total_sec / 3600, 1)

        achievements = []
        if total_sec >= 900:
            achievements.append({"id": "first_watch", "title": "Первый сеанс", "desc": "Посмотрел 15 минут видео", "icon": "🍿"})
        if total_sec >= 3600 * 5:
            achievements.append({"id": "movie_fan", "title": "Киноман", "desc": "5+ часов совместного просмотра", "icon": "🎬"})
        if total_sec >= 3600 * 25:
            achievements.append({"id": "marathoner", "title": "Марафонец", "desc": "25+ часов просмотра в комнатах", "icon": "🏆"})
        if total_sec >= 3600 * 100:
            achievements.append({"id": "legend", "title": "Легенда VD", "desc": "100+ часов совместных видео", "icon": "👑"})
        if stats.get("rooms_created", 0) >= 1:
            achievements.append({"id": "host", "title": "Душа компании", "desc": "Создал собственную комнату", "icon": "👥"})
        if stats.get("movies_count", 0) >= 5:
            achievements.append({"id": "critic", "title": "Кинокритик", "desc": "Посмотрел 5 разных фильмов/шоу", "icon": "⭐"})

        stats["hours"] = hours
        stats["level"] = level
        stats["achievements"] = achievements
        stats["weekly_chart"] = [
            {"day": "Пн", "hours": round(stats.get("day_mon_sec", 0) / 3600, 2)},
            {"day": "Вт", "hours": round(stats.get("day_tue_sec", 0) / 3600, 2)},
            {"day": "Ср", "hours": round(stats.get("day_wed_sec", 0) / 3600, 2)},
            {"day": "Чт", "hours": round(stats.get("day_thu_sec", 0) / 3600, 2)},
            {"day": "Пт", "hours": round(stats.get("day_fri_sec", 0) / 3600, 2)},
            {"day": "Сб", "hours": round(stats.get("day_sat_sec", 0) / 3600, 2)},
            {"day": "Вс", "hours": round(stats.get("day_sun_sec", 0) / 3600, 2)},
        ]
        return stats

def get_user_watch_history(user_id: int, limit: int = 15) -> List[Dict[str, Any]]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        SELECT id, title, poster, url, media_type, duration_sec, watched_sec, updated_at
        FROM watch_history
        WHERE user_id = ?
        ORDER BY updated_at DESC
        LIMIT ?
        """, (user_id, limit))
        return [dict(r) for r in cursor.fetchall()]

def increment_room_created(user_id: int):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE user_stats SET rooms_created = rooms_created + 1 WHERE user_id = ?", (user_id,))
        conn.commit()

def increment_messages_sent(user_id: int):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE user_stats SET messages_sent = messages_sent + 1 WHERE user_id = ?", (user_id,))
        conn.commit()


# ================================= FRIENDS & DUO REPOSITORY =================================

def add_friendship(user_id1: int, user_id2: int):
    if not user_id1 or not user_id2 or user_id1 == user_id2:
        return
    now_ts = time.time()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        INSERT OR IGNORE INTO friends (user_id, friend_id, status, created_at)
        VALUES (?, ?, 'accepted', ?)
        """, (user_id1, user_id2, now_ts))
        cursor.execute("""
        INSERT OR IGNORE INTO friends (user_id, friend_id, status, created_at)
        VALUES (?, ?, 'accepted', ?)
        """, (user_id2, user_id1, now_ts))
        conn.commit()
        backup_database_to_json()

def add_friend_by_username(user_id: int, friend_username: str) -> Optional[Dict[str, Any]]:
    target = get_user_by_username(friend_username.strip())
    if not target or target["id"] == user_id:
        return None
    add_friendship(user_id, target["id"])
    return target

def remove_friendship(user_id1: int, user_id2: int):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM friends WHERE (user_id = ? AND friend_id = ?) OR (user_id = ? AND friend_id = ?)",
                       (user_id1, user_id2, user_id2, user_id1))
        conn.commit()
        backup_database_to_json()

def are_friends(user_id1: Any, user_id2: Any) -> bool:
    try:
        u1 = int(user_id1)
        u2 = int(user_id2)
    except (ValueError, TypeError):
        return False
    if u1 == u2:
        return True
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM friends WHERE user_id = ? AND friend_id = ? AND status = 'accepted'", (u1, u2))
        return bool(cursor.fetchone())

def touch_user_activity(user_id: Any):
    """Update last_seen timestamp for active presence tracking."""
    try:
        uid = int(user_id)
        now_ts = time.time()
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET last_seen = ? WHERE id = ?", (now_ts, uid))
            conn.commit()
    except Exception:
        pass

def update_user_status(user_id: Any, status: str):
    """Update user status ('online' or 'offline') and last_seen timestamp."""
    try:
        uid = int(user_id)
        now_ts = time.time()
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET status = ?, last_seen = ? WHERE id = ?", (status, now_ts, uid))
            conn.commit()
    except Exception:
        pass

def get_user_friends(user_id: int) -> List[Dict[str, Any]]:
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
        SELECT u.id, u.username, u.display_name, u.avatar, u.status, u.last_seen
        FROM friends f
        JOIN users u ON f.friend_id = u.id
        WHERE f.user_id = ? AND f.status = 'accepted'
        ORDER BY u.last_seen DESC
        """, (user_id,))
        return [dict(r) for r in cursor.fetchall()]

# Auto-initialize DB on import
init_db()

