import re
import json
import time
import urllib.request
import urllib.parse

import ssl

import concurrent.futures

from typing import Dict, Any, Optional, List

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

_CACHE: Dict[str, Any] = {}
_CACHE_EXPIRE: Dict[str, float] = {}

_SSL_CTX = ssl.create_default_context()
_SSL_CTX.check_hostname = False
_SSL_CTX.verify_mode = ssl.CERT_NONE

def detect_audio_lang(name: str) -> str:
    n = (name or "").lower()
    if any(k in n for k in ["укр", "ukr", "1+1", "ictv", "стб", "інтер", "новий", "нова", "postmodern", "le doyen", "цікава", "dniprofilm", "третякоф", "бамбук", "всі"]):
        return "uk"
    if any(k in n for k in ["eng", "ориг", "orig", "english", "original"]):
        return "en"
    return "ru"

CURATED_MEDIA_CATALOG: List[Dict[str, Any]] = [
    {
        "id": "kp_161268",
        "kp_id": "161268",
        "imdb_id": "tt0206512",
        "title": "Губка Боб Квадратні Штани / Губка Боб",
        "original_title": "SpongeBob SquarePants",
        "year": "1999–2026",
        "type": "series",
        "rating": "8.2",
        "poster": "https://m.media-amazon.com/images/M/MV5BMTY2NGUzMWItYjE3Zi00YWFiLTlmYzYtMjYwZjM3YWMxMDRiXkEyXkFqcGc@._V1_.jpg",
        "backdrop": "https://m.media-amazon.com/images/M/MV5BMjMwMjgyOTYyNF5BMl5BanBnXkFtZTgwNTQ5Mzk3NTM@._V1_.jpg",
        "description": "Культовий комедійний мультсеріал про життя життєрадісної морської губки Боба та його друзів Патріка, Сквідварда і Сенді на дні океану в містечку Бікіні Боттом.",
        "badges": ["🇺🇦 1+1 (Укр)", "🇷🇺 Дубляж", "🇬🇧 Eng.Original"],
        "has_ukr": True,
        "has_ru": True
    },
    {
        "id": "kp_35526",
        "kp_id": "35526",
        "imdb_id": "tt0345950",
        "title": "Губка Боб Квадратні Штани (Фільм 2004)",
        "original_title": "The SpongeBob SquarePants Movie",
        "year": "2004",
        "type": "movie",
        "rating": "7.2",
        "poster": "https://m.media-amazon.com/images/M/MV5BNmU4M2E3MDktNmE5YS00N2EzLThmYWYtODFkNTM2MGM5ODFmXkEyXkFqcGc@._V1_.jpg",
        "backdrop": "",
        "description": "Боб та Патрік вирушають у повну пригод подорож до Шелл-Сіті, щоб повернути викрадену корону владики Нептуна і врятувати містера Крабса.",
        "badges": ["🇺🇦 Дубляж (Укр)", "🇷🇺 Дубляж", "🇬🇧 Eng.Original"],
        "has_ukr": True,
        "has_ru": True
    },
    {
        "id": "kp_679486",
        "kp_id": "679486",
        "imdb_id": "tt2279373",
        "title": "Губка Боб в 3D",
        "original_title": "The SpongeBob Movie: Sponge Out of Water",
        "year": "2015",
        "type": "movie",
        "rating": "6.0",
        "poster": "https://m.media-amazon.com/images/M/MV5BMTQzMjYwMjUwNF5BMl5BanBnXkFtZTgwNzYwNDgyNDE@._V1_.jpg",
        "backdrop": "",
        "description": "Пірат Бургеробород викрадає чарівну книгу з рецептом крабсбургера. Губка Боб разом із друзями виходить у світ людей.",
        "badges": ["🇺🇦 Le Doyen (Укр)", "🇷🇺 Дубляж", "🇬🇧 Eng.Original"],
        "has_ukr": True,
        "has_ru": True
    },
    {
        "id": "kp_933215",
        "kp_id": "933215",
        "imdb_id": "tt4823776",
        "title": "Губка Боб у бігах / Губка Боб в бегах",
        "original_title": "The SpongeBob Movie: Sponge on the Run",
        "year": "2020",
        "type": "movie",
        "rating": "6.5",
        "poster": "https://m.media-amazon.com/images/M/MV5BZTBiZDQ2MWEtYzE1MC00YmMyLTg1NjUtNzE2YTZlMjI3MGUxXkEyXkFqcGc@._V1_.jpg",
        "backdrop": "",
        "description": "Коли домашнього улюбленця Гері викрадають, Губка Боб і Патрік вирушають у небезпечну рятувальну місію до Атлантік-Сіті.",
        "badges": ["🇺🇦 Le Doyen (Укр)", "🇷🇺 Дубляж", "🇬🇧 Eng.Original"],
        "has_ukr": True,
        "has_ru": True
    },
    {
        "id": "kp_258687",
        "kp_id": "258687",
        "imdb_id": "tt0816692",
        "title": "Інтерстеллар / Интерстеллар",
        "original_title": "Interstellar",
        "year": "2014",
        "type": "movie",
        "rating": "8.7",
        "poster": "https://m.media-amazon.com/images/M/MV5BYzdjMDAxZGItMjI2My00ODA1LTlkNzItOWFjMDU5ZDJlYWY3XkEyXkFqcGc@._V1_.jpg",
        "backdrop": "https://m.media-amazon.com/images/M/MV5BMTY3NTc2NDk0NV5BMl5BanBnXkFtZTgwNjA2MjM5MDE@._V1_.jpg",
        "description": "Коли Земля стає непридатною для життя, група сміливих дослідників вирушає крізь червоточину в пошуках нової планети для людства.",
        "badges": ["🇺🇦 Постмодерн (Укр)", "🇷🇺 Дубляж", "🇬🇧 Eng.Original"],
        "has_ukr": True,
        "has_ru": True
    },
    {
        "id": "kp_4366627",
        "kp_id": "4366627",
        "imdb_id": "tt3581920",
        "title": "Останні з нас / Одни из нас",
        "original_title": "The Last of Us",
        "year": "2023–2025",
        "type": "series",
        "rating": "8.8",
        "poster": "https://m.media-amazon.com/images/M/MV5BYzA2NzRmMWItNzVhNC00NTExLWJkYWItYmZhZDA5OTQ1YTAxXkEyXkFqcGc@._V1_.jpg",
        "backdrop": "",
        "description": "Загартований виживальник Джоел отримує завдання провести 14-річну дівчинку Еллі крізь спустошені руїни постапокаліптичних США.",
        "badges": ["🇺🇦 Цікава Ідея (Укр)", "🇷🇺 Red Head Sound", "🇬🇧 Eng.Original"],
        "has_ukr": True,
        "has_ru": True
    },
    {
        "id": "kp_404900",
        "kp_id": "404900",
        "imdb_id": "tt0903747",
        "title": "Пуститися берега / Во все тяжкие",
        "original_title": "Breaking Bad",
        "year": "2008–2013",
        "type": "series",
        "rating": "9.5",
        "poster": "https://m.media-amazon.com/images/M/MV5BMzU5ZGYzNmQtMTdhYy00OGRiLTg0NmQtYjVjNzliZTg1ZGE4XkEyXkFqcGc@._V1_.jpg",
        "backdrop": "",
        "description": "Учитель хімії Волтер Вайт дізнається про невиліковну хворобу і разом із колишнім учнем береться за виробництво метамфетаміну.",
        "badges": ["🇺🇦 1+1 (Укр)", "🇷🇺 LostFilm", "🇬🇧 Eng.Original"],
        "has_ukr": True,
        "has_ru": True
    },
    {
        "id": "kp_505898",
        "kp_id": "505898",
        "imdb_id": "tt1630029",
        "title": "Аватар: Шлях води / Аватар: Путь воды",
        "original_title": "Avatar: The Way of Water",
        "year": "2022",
        "type": "movie",
        "rating": "7.6",
        "poster": "https://m.media-amazon.com/images/M/MV5BNWI0Y2NkOWEtMmM2OC00MjQ3LWI1YzItZGQxYzQ3NzI4NWZmXkEyXkFqcGc@._V1_.jpg",
        "backdrop": "",
        "description": "Джейк Саллі та Нейтірі разом зі своїми дітьми змушені шукати притулок біля водного рифового клану Меткаїна на Пандорі.",
        "badges": ["🇺🇦 Postmodern (Укр)", "🇷🇺 Дубляж", "🇬🇧 Eng.Original"],
        "has_ukr": True,
        "has_ru": True
    },
    {
        "id": "kp_4664634",
        "kp_id": "4664634",
        "imdb_id": "tt15239678",
        "title": "Дюна: Частина друга / Дюна: Часть вторая",
        "original_title": "Dune: Part Two",
        "year": "2024",
        "type": "movie",
        "rating": "8.5",
        "poster": "https://m.media-amazon.com/images/M/MV5BNTc0YmQxMjEtODI5MC00NjFiLTlkMWUtOGQ5NjFmYWUyZGJhXkEyXkFqcGc@._V1_.jpg",
        "backdrop": "",
        "description": "Пол Атрід об'єднується з Чані та вільними фременами, готуючи масштабну помсту змовникам, які знищили його дім.",
        "badges": ["🇺🇦 Postmodern (Укр)", "🇷🇺 Дубляж", "🇬🇧 Eng.Original"],
        "has_ukr": True,
        "has_ru": True
    }
]

def get_cache(key: str) -> Optional[Any]:
    if key in _CACHE and time.time() < _CACHE_EXPIRE.get(key, 0):
        return _CACHE[key]
    return None

def set_cache(key: str, val: Any, ttl: int = 300):
    _CACHE[key] = val
    _CACHE_EXPIRE[key] = time.time() + ttl

def strip_html_tags(text: str) -> str:
    if not text:
        return ""
    clean = re.sub(r'<[^>]+>', ' ', text)
    clean = clean.replace('&nbsp;', ' ').replace('&mdash;', '—').replace('&ndash;', '–').replace('&quot;', '"').replace('&laquo;', '«').replace('&raquo;', '»').replace('&rsquo;', "'").replace('&amp;', '&')
    return re.sub(r'\s+', ' ', clean).strip()

class VideoResolver:
    @staticmethod
    def fetch_url(url: str, headers: Optional[Dict[str, str]] = None, timeout: int = 8) -> str:
        req_headers = {"User-Agent": USER_AGENT}
        if headers:
            req_headers.update(headers)
        req = urllib.request.Request(url, headers=req_headers)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8", errors="ignore")

    @staticmethod
    def fetch_json(url: str, headers: Optional[Dict[str, str]] = None, timeout: int = 8) -> Any:
        content = VideoResolver.fetch_url(url, headers, timeout)
        return json.loads(content)

    @classmethod
    def resolve_starlight_hash(cls, hash_val: str, referer: str = "https://teleportal.ua") -> Optional[Dict[str, Any]]:
        cached = get_cache(f"hash_{hash_val}")
        if cached:
            return cached

        api_url = f"https://vcms-api2.starlight.digital/player-api/{hash_val}?referer={urllib.parse.quote(referer)}&lang=ua"
        headers = {
            "Referer": "https://player.starlight.digital/",
            "Origin": "https://player.starlight.digital"
        }
        try:
            data = cls.fetch_json(api_url, headers=headers)
            video_list = data.get("video", [])
            if not video_list:
                return None
            v = video_list[0]
            stream_url = v.get("mediaHlsNoAdv") or v.get("mediaHls") or ""
            if not stream_url and "media" in v and v["media"]:
                stream_url = v["media"][0].get("url", "")

            title = v.get("name") or data.get("name") or "Відео"
            poster = v.get("poster") or data.get("poster") or ""
            duration = float(v.get("duration") or 0.0)

            if stream_url:
                res = {
                    "type": "hls",
                    "url": stream_url,
                    "title": title,
                    "poster": poster,
                    "duration": duration,
                    "source": "starlight",
                    "hash": hash_val,
                    "needs_proxy": False
                }
                set_cache(f"hash_{hash_val}", res, ttl=3600)
                return res
        except Exception:
            pass
        return None

    @classmethod
    def resolve_novy_or_stb(cls, url: str) -> Optional[Dict[str, Any]]:
        try:
            html = cls.fetch_url(url, headers={"Referer": url})
            # 1. Search player.starlight.digital/([a-f0-9]{32,64})
            m = re.search(r'player\.starlight\.digital\/([a-f0-9]{32,64})', html)
            if m:
                return cls.resolve_starlight_hash(m.group(1), referer=url)

            # 2. Search vcms hash
            m = re.search(r'hash["\']?\s*:\s*["\']([a-f0-9]{32,64})["\']', html)
            if m:
                return cls.resolve_starlight_hash(m.group(1), referer=url)

            # 3. Direct m3u8
            m = re.search(r'(https?:\/\/[^"\'\s]+\.m3u8[^"\'\s]*)', html)
            if m:
                return {
                    "type": "hls",
                    "url": m.group(1),
                    "title": "Відео (HLS)",
                    "poster": "",
                    "duration": 0
                }
        except Exception:
            pass
        return None

    @classmethod
    def resolve_teleportal(cls, url: str) -> Optional[Dict[str, Any]]:
        # Fast path: if url contains a 32 or 64 hex hash
        m_hash = re.search(r'([a-f0-9]{64}|[a-f0-9]{32})', url)
        if m_hash:
            res = cls.resolve_starlight_hash(m_hash.group(1), referer=url)
            if res:
                return res

        parsed = urllib.parse.urlparse(url)
        path = parsed.path.strip("/")
        parts = [p for p in path.split("/") if p]
        
        lang = "ua"
        if parts and parts[0] in ("ua", "ru"):
            lang = parts.pop(0)
            
        if len(parts) >= 5:
            type_slug, channel_slug, project_slug, season_slug, video_slug = parts[:5]
            api_url = f"https://tp-back.starlight.digital/{lang}/{type_slug}/{channel_slug}/{project_slug}/{season_slug}/{video_slug}"
            try:
                headers = {"Origin": "https://teleportal.ua", "Referer": "https://teleportal.ua/"}
                data = cls.fetch_json(api_url, headers=headers)
                hash_val = data.get("hash")
                if not hash_val:
                    v_link = data.get("video", "")
                    m = re.search(r'([a-f0-9]{32,64})', v_link)
                    if m:
                        hash_val = m.group(1)
                
                if hash_val:
                    res = cls.resolve_starlight_hash(hash_val, referer=url)
                    if res:
                        if data.get("title"):
                            res["title"] = f"{data.get('projectTitle') or data.get('projectName') or ''} - {data.get('title')}".strip(" -")
                        return res
            except Exception:
                pass

        try:
            html = cls.fetch_url(url, headers={"Referer": "https://teleportal.ua/"})
            m = re.search(r'([a-f0-9]{64})', html)
            if m:
                return cls.resolve_starlight_hash(m.group(1), referer=url)
        except Exception:
            pass

        return None

    @classmethod
    def resolve_youtube(cls, url: str) -> Optional[Dict[str, Any]]:
        patterns = [
            r'(?:youtu\.be\/|youtube\.com\/(?:watch\?v=|shorts\/|embed\/))([a-zA-Z0-9_-]{11})',
        ]
        for pat in patterns:
            m = re.search(pat, url)
            if m:
                yt_id = m.group(1)
                title = f"YouTube ({yt_id})"
                author = "YouTube"
                try:
                    oembed_url = f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={yt_id}&format=json"
                    data = cls.fetch_json(oembed_url, timeout=3)
                    if data.get("title"):
                        title = data["title"]
                    if data.get("author_name"):
                        author = data["author_name"]
                except Exception:
                    pass
                return {
                    "type": "youtube",
                    "id": yt_id,
                    "url": f"https://www.youtube.com/watch?v={yt_id}",
                    "title": title,
                    "author": author,
                    "poster": f"https://img.youtube.com/vi/{yt_id}/hqdefault.jpg",
                    "duration": 0
                }
        return None

    @classmethod
    def resolve_ytdlp(cls, url: str) -> Optional[Dict[str, Any]]:
        if not (url.startswith("http://") or url.startswith("https://")):
            return None
        if any(d in url for d in ["namy.ws", "kodikplayer.com", "tapeop.dev", "rstprgapipt", "kinodivbox", "newplayjj"]):
            return None
        try:
            import yt_dlp
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'skip_download': True,
                'format': 'best[ext=mp4][acodec!=none][vcodec!=none]/best[acodec!=none][vcodec!=none]/best'
            }
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                stream_url = info.get("url")
                # If chosen stream has no audio, search formats for a stream with audio
                if stream_url and info.get("acodec") == "none":
                    stream_url = None

                if not stream_url and "formats" in info:
                    # Priority 1: Both video and audio
                    for f in reversed(info["formats"]):
                        if f.get("url") and f.get("acodec") and f.get("acodec") != "none" and f.get("vcodec") and f.get("vcodec") != "none":
                            stream_url = f["url"]
                            break
                    # Priority 2: At least audio codec exists
                    if not stream_url:
                        for f in reversed(info["formats"]):
                            if f.get("url") and f.get("acodec") and f.get("acodec") != "none":
                                stream_url = f["url"]
                                break
                    # Priority 3: Fallback to any valid url
                    if not stream_url:
                        for f in reversed(info["formats"]):
                            if f.get("url"):
                                stream_url = f["url"]
                                break
                if not stream_url:
                    return None
                type_ = "hls" if ".m3u8" in stream_url else "mp4"
                return {
                    "type": type_,
                    "url": stream_url,
                    "title": info.get("title") or "Видео",
                    "poster": info.get("thumbnail") or "",
                    "duration": float(info.get("duration") or 0.0),
                    "source": "ytdlp"
                }
        except Exception:
            return None

    @classmethod
    def resolve_megogo(cls, url: str) -> Optional[Dict[str, Any]]:
        """Extracts Megogo movie/series and resolves it into a high quality player with dubbings."""
        movie_title = ""
        try:
            html = cls.fetch_url(url, headers={"User-Agent": USER_AGENT, "Referer": "https://megogo.net/"}, timeout=5)
            m = re.search(r'<meta[^>]+property=["\']og:title["\'][^>]+content=["\']([^"\']+)["\']', html)
            if m:
                movie_title = m.group(1)
            if not movie_title:
                h1 = re.search(r'<h1[^>]*>([^<]+)</h1>', html)
                if h1:
                    movie_title = h1.group(1)
        except Exception:
            pass

        if not movie_title:
            m_slug = re.search(r'/view/\d+-([a-zA-Z0-9_\-]+?)(?:-trailer)?\.html', url)
            if m_slug:
                movie_title = m_slug.group(1).replace("-", " ").strip()

        if movie_title:
            movie_title = re.sub(r'\(.*?(?:трейлер|trailer).*?\)', '', movie_title, flags=re.I)
            movie_title = re.sub(r'(?:дивитися|смотреть)\s+онлайн.*', '', movie_title, flags=re.I)
            movie_title = movie_title.strip(" «»\"'")
            if movie_title:
                res = cls.resolve_movie_by_title(movie_title)
                res["title"] = f"{movie_title} (Megogo · с выбором озвучки)"
                return res

        return None

    @classmethod
    def resolve(cls, raw_url: str) -> Dict[str, Any]:
        url = str(raw_url or "").strip()
        if not url:
            return {"type": "none", "url": "", "title": ""}

        # Internal direct disk and local stream endpoints
        if url.startswith("/stream/") or url.startswith("/stream_disk/") or url.startswith("/stream_local/"):
            return {
                "type": "mp4",
                "url": url,
                "title": "Локальное видео",
                "poster": "",
                "duration": 0
            }

        # Internal proxy stream endpoints
        if url.startswith("/api/hls/proxy"):
            return {
                "type": "hls",
                "url": url,
                "title": "HLS Stream",
                "poster": "",
                "duration": 0
            }
        if url.startswith("/api/proxy/stream"):
            return {
                "type": "mp4",
                "url": url,
                "title": "Proxy Video",
                "poster": "",
                "duration": 0
            }

        # Pixeldrain direct stream (wrapped via proxy to eliminate ORB blocking)
        m_pixel = re.search(r'(?:pixeldrain\.com|xeldrain\.com|pd\.to)/(?:u|api/file)/([a-zA-Z0-9_-]+)', url)
        if m_pixel:
            fid = m_pixel.group(1)
            direct_url = f"https://pixeldrain.com/api/file/{fid}"
            proxied_url = f"/api/proxy/stream?url={urllib.parse.quote(direct_url, safe='')}"
            p_title = "Pixeldrain Video"
            p_poster = f"https://pixeldrain.com/api/file/{fid}/thumbnail"
            try:
                r_info = requests.get(f"https://pixeldrain.com/api/file/{fid}/info", timeout=2.5, headers={"User-Agent": "Mozilla/5.0"})
                if r_info.status_code == 200:
                    info_json = r_info.json()
                    if info_json.get("name"):
                        p_title = info_json["name"]
            except Exception:
                pass
            return {
                "type": "mp4",
                "url": proxied_url,
                "title": p_title,
                "poster": p_poster,
                "duration": 0
            }

        # Direct HLS or MP4 stream links (Checked FIRST before hash resolution!)
        if re.search(r'\.m3u8(\?|$)', url, re.I):
            return {
                "type": "hls",
                "url": url,
                "title": "Прямой видеопоток",
                "poster": "",
                "duration": 0
            }
        if re.search(r'\.(mp4|webm|ogg|mov|mkv|m4v)(\?|$)', url, re.I):
            return {
                "type": "mp4",
                "url": url,
                "title": "Прямое видео",
                "poster": "",
                "duration": 0
            }

        # 1. YouTube
        yt = cls.resolve_youtube(url)
        if yt:
            return yt

        # 2. Starlight / Teleportal direct hash (Only if NOT already a direct m3u8/mp4 link!)
        m_hash = re.search(r'([a-f0-9]{64}|[a-f0-9]{32})', url)
        if m_hash and ("starlight" in url or "teleportal" in url or "player" in url or len(url.strip()) in (32, 64)):
            sl_res = cls.resolve_starlight_hash(m_hash.group(1), referer="https://teleportal.ua")
            if sl_res:
                return sl_res

        # 4. Teleportal.ua
        if "teleportal.ua" in url:
            tp = cls.resolve_teleportal(url)
            if tp:
                return tp

        # 5. Megogo.net
        if "megogo.net" in url:
            mg = cls.resolve_megogo(url)
            if mg:
                return mg

        # 6. Novy Kanal, STB, ICTV
        if any(d in url for d in ["novy.tv", "stb.ua", "ictv.ua"]):
            tv = cls.resolve_novy_or_stb(url)
            if tv:
                return tv

        # 6. Generic extraction via yt-dlp
        ydl = cls.resolve_ytdlp(url)
        if ydl:
            return ydl

        # 7. Fallback: Iframe Embed
        if url.startswith("http://") or url.startswith("https://"):
            return {
                "type": "embed",
                "url": url,
                "title": "Веб-плеєр (Embed)",
                "poster": "",
                "duration": 0
            }

        return {"type": "none", "url": "", "title": ""}

    @classmethod
    def get_project_details(cls, type_slug: str, channel_slug: str, project_slug: str, lang: str = "ua") -> Dict[str, Any]:
        # Robust normalization to prevent any cross-series mixup
        proj_clean = (project_slug or "").strip().lower()
        if proj_clean in ("budynochok", "budynochok-na-shchastya", "budynochok_na_shchastya", "budinochok", "domik"):
            project_slug = "domik"
            type_slug = "serials"
            channel_slug = "novyy-kanal"
        elif proj_clean in ("supermama", "супермама"):
            project_slug = "supermama"
            type_slug = "show"
            channel_slug = "stb"

        cache_key = f"proj_{type_slug}_{channel_slug}_{project_slug}_{lang}"
        cached = get_cache(cache_key)
        if cached and cached.get("seasons"):
            return cached

        api_url = f"https://tp-back.starlight.digital/{lang}/{type_slug}/{channel_slug}/{project_slug}"
        headers = {"Origin": "https://teleportal.ua", "Referer": "https://teleportal.ua/"}
        try:
            data = cls.fetch_json(api_url, headers=headers)
            title = data.get("title") or data.get("projectName") or ""
            desc = strip_html_tags(data.get("description") or "")
            seasons_gallery = data.get("seasonsGallery", [])
            seasons = []
            for s in seasons_gallery:
                season_title = s.get("title") or "Сезон"
                season_slug = s.get("seasonSlug") or ""
                episodes = []
                for ep in s.get("items", []):
                    img = ep.get("image") or ep.get("imageMob") or ""
                    if img and not img.startswith("http"):
                        img = "https://teleportal.ua" + img
                    
                    series_title = ep.get("seriesTitle") or ""
                    raw_title = ep.get("title") or ""
                    
                    # Clean title: strip redundant show names
                    clean_t = raw_title
                    for prefix in ["Будиночок на щастя", "Супермама", title]:
                        if prefix:
                            clean_t = re.sub(rf'^{re.escape(prefix)}[.\s-]*', '', clean_t, flags=re.I)
                    clean_t = clean_t.strip(" .-")
                    if not clean_t or len(clean_t) < 3:
                        clean_t = f"Серія {series_title}" if series_title else raw_title

                    dur = ep.get("duration")
                    if dur is not None:
                        try:
                            dur_num = float(dur)
                            if dur_num > 100000:
                                dur_num = dur_num / 1000.0
                            dur = round(dur_num)
                        except (ValueError, TypeError):
                            pass

                    episodes.append({
                        "title": clean_t,
                        "raw_title": raw_title,
                        "seriesTitle": series_title,
                        "videoSlug": ep.get("videoSlug"),
                        "hash": ep.get("hash"),
                        "duration": dur,
                        "image": img,
                        "poster": img,
                        "date": ep.get("dateOfBroadcast", "")
                    })
                seasons.append({
                    "title": season_title,
                    "slug": season_slug,
                    "episodes": episodes
                })
            res = {"title": title, "description": desc, "seasons": seasons}
            if seasons:
                set_cache(cache_key, res, ttl=600)
            return res
        except Exception:
            return {"title": "", "seasons": []}

    @classmethod
    def get_featured_content(cls) -> Dict[str, Any]:
        """User only watches: Supermama (STB) and Budynochok na schastya (Novyy Kanal). Clean & clutter-free!"""
        cached = get_cache("clean_featured_content_v2")
        if cached:
            return cached

        curated = [
            {
                "id": "supermama",
                "title": "Супермама",
                "channel": "СТБ",
                "channelSlug": "stb",
                "typeSlug": "show",
                "projectSlug": "supermama",
                "badge": "Новий випуск 12 сезон",
                "tag": "СТБ Шоу",
                "bg": "https://teleportal.ua/storage/editor/fotos/supermama_1790242886312.jpg"
            },
            {
                "id": "domik",
                "title": "Будиночок на щастя",
                "channel": "Новий Канал",
                "channelSlug": "novyy-kanal",
                "typeSlug": "serials",
                "projectSlug": "domik",
                "badge": "7 Сезон 2026",
                "tag": "Новий Канал",
                "bg": "https://teleportal.ua/storage/editor/fotos/domyk-na-schaste_1791280603145.jpg"
            }
        ]

        hero_banners = []
        shows_list = []
        for c in curated:
            details = cls.get_project_details(c["typeSlug"], c["channelSlug"], c["projectSlug"])
            latest_ep = None
            if details.get("seasons") and details["seasons"][0].get("episodes"):
                latest_ep = details["seasons"][0]["episodes"][0]

            item = {
                **c,
                "description": details.get("description", ""),
                "latest_episode": latest_ep,
                "seasons_count": len(details.get("seasons", []))
            }
            shows_list.append(item)
            hero_banners.append(item)

        res = {
            "hero": hero_banners,
            "shows": shows_list
        }
        set_cache("clean_featured_content_v2", res, ttl=600)
        return res

    @classmethod
    def resolve_movie_by_title(cls, title: str) -> Dict[str, Any]:
        """Provides a direct, working embed player for ANY movie or TV series with voice acting selection!"""
        title = clean_text(title, 100)
        if not title:
            return {"type": "none", "url": "", "title": ""}
        
        # 1. Direct Kinopoisk / IMDb ID check
        m_kp = re.search(r'kinopoisk\.ru/(?:film|series)/(\d+)', title)
        if m_kp:
            kp_id = m_kp.group(1)
            return {
                "type": "embed",
                "url": f"https://api.namy.ws/embed/kp/{kp_id}",
                "title": f"Кинопоиск #{kp_id} (с выбором озвучки)",
                "source": "collaps"
            }
        if title.isdigit():
            return {
                "type": "embed",
                "url": f"https://api.namy.ws/embed/kp/{title}",
                "title": f"Кинопоиск #{title} (с выбором озвучки)",
                "source": "collaps"
            }
        if title.startswith("tt") and title[2:].isdigit():
            return {
                "type": "embed",
                "url": f"https://api.namy.ws/embed/imdb/{title}",
                "title": f"IMDb {title} (с выбором озвучки)",
                "source": "collaps"
            }

        # 2. Try Wikipedia / Wikidata entity search for Kinopoisk & IMDb ID
        try:
            q_enc = urllib.parse.quote(title)
            wiki_url = f"https://ru.wikipedia.org/w/api.php?action=query&list=search&srsearch={q_enc}&format=json"
            headers = {"User-Agent": "RaveWatchParty/2.0 (contact@rave.local)"}
            data = cls.fetch_json(wiki_url, headers=headers, timeout=4)
            search_results = data.get("query", {}).get("search", [])
            if search_results:
                pageid = search_results[0]["pageid"]
                matched_title = search_results[0]["title"]
                prop_url = f"https://ru.wikipedia.org/w/api.php?action=query&prop=pageprops&ppprop=wikibase_item&pageids={pageid}&format=json"
                pdata = cls.fetch_json(prop_url, headers=headers, timeout=4)
                item = pdata.get("query", {}).get("pages", {}).get(str(pageid), {}).get("pageprops", {}).get("wikibase_item")
                if item:
                    wd_url = f"https://www.wikidata.org/wiki/Special:EntityData/{item}.json"
                    wd = cls.fetch_json(wd_url, headers=headers, timeout=4)
                    claims = wd.get("entities", {}).get(item, {}).get("claims", {})
                    kp_val = claims.get("P2603", [{}])[0].get("mainsnak", {}).get("datavalue", {}).get("value")
                    imdb_val = claims.get("P345", [{}])[0].get("mainsnak", {}).get("datavalue", {}).get("value")
                    
                    if kp_val:
                        return {
                            "type": "embed",
                            "url": f"https://api.namy.ws/embed/kp/{kp_val}",
                            "title": f"{matched_title} (с выбором озвучки)",
                            "source": "collaps",
                            "kp_id": str(kp_val),
                            "imdb_id": imdb_val or ""
                        }
                    elif imdb_val and str(imdb_val).startswith("tt"):
                        return {
                            "type": "embed",
                            "url": f"https://api.namy.ws/embed/imdb/{imdb_val}",
                            "title": f"{matched_title} (с выбором озвучки)",
                            "source": "collaps",
                            "imdb_id": str(imdb_val)
                        }
        except Exception:
            pass

        # 3. Universal Kodik balancer search player (works directly with title & all dubbing studios)
        encoded = urllib.parse.quote(title)
        player_url = f"https://kodikplayer.com/find-player?title={encoded}"
        
        return {
            "type": "embed",
            "url": player_url,
            "title": f"{title} (с выбором озвучки)",
            "poster": "",
            "duration": 0,
            "source": "kodik"
        }


    @classmethod
    def search_catalog(cls, query: str, limit: int = 15) -> List[Dict[str, Any]]:
        q = (query or "").strip()
        if not q:
            return CURATED_MEDIA_CATALOG[:limit]

        cache_key = f"catalog_search_v3_{q.lower()}"
        cached = get_cache(cache_key)
        if cached is not None:
            return cached

        q_words = [w.lower() for w in re.findall(r'\w+', q) if len(w) > 1]
        has_cyrillic = bool(re.search(r'[а-яіїєґ]', q.lower()))

        seen_kp = set()
        seen_imdb = set()
        seen_titles = set()
        scored_results: List[tuple] = []

        def add_candidate(item: Dict[str, Any], priority_bonus: int = 0):
            kp = (item.get("kp_id") or "").strip()
            imdb = (item.get("imdb_id") or "").strip()
            raw_t = (item.get("title") or "").strip()
            t_low = raw_t.lower()

            if kp and kp in seen_kp:
                return
            if imdb and imdb in seen_imdb:
                return
            if t_low and t_low in seen_titles:
                return

            full_text = f"{t_low} {(item.get('original_title') or '').lower()}"
            matched_words = sum(1 for w in q_words if w in full_text)
            
            # If search query has 2+ words, item must match at least 1 word
            if q_words and matched_words == 0 and priority_bonus == 0:
                return

            # Score computation
            score = (matched_words * 15) + priority_bonus
            # Bonus for exact full phrase match
            if q.lower() in t_low:
                score += 25

            # Penalize pure English titles when user typed in Russian/Ukrainian
            is_pure_english = bool(re.match(r'^[a-zA-Z0-9\s:,\.\-\'"]+$', raw_t))
            if is_pure_english and has_cyrillic:
                score -= 12

            if kp: seen_kp.add(kp)
            if imdb: seen_imdb.add(imdb)
            if t_low: seen_titles.add(t_low)

            scored_results.append((score, item))

        # 1. Exact match on Curated Catalog (high priority +20)
        q_low = q.lower()
        for item in CURATED_MEDIA_CATALOG:
            t_low = (item.get("title") or "").lower()
            ot_low = (item.get("original_title") or "").lower()
            if any(w in t_low or w in ot_low for w in q_words) or (item.get("kp_id") and q_low == item["kp_id"]):
                add_candidate(item, priority_bonus=20)

        # 2. Match Teleportal shows (Supermama / Budynochok)
        if any(w in q_low for w in ["супер", "мама", "supermama"]):
            sm = cls.get_project_details("show", "stb", "supermama", "ua")
            add_candidate({
                "id": "teleportal_supermama",
                "title": "Супермама (СТБ)",
                "original_title": "Supermama STB",
                "year": "2020–2026",
                "type": "series",
                "rating": "8.4",
                "poster": "https://teleportal.ua/storage/editor/fotos/supermama_1790242886312.jpg",
                "description": sm.get("description") or "Психологічне сімейне реаліті-шоу на СТБ.",
                "badges": ["🇺🇦 СТБ Оригінал"],
                "has_ukr": True,
                "has_ru": False,
                "source": "teleportal",
                "teleportal": {"type": "show", "channel": "stb", "project": "supermama"}
            }, priority_bonus=25)
        if any(w in q_low for w in ["будин", "домик", "щастя", "domik"]):
            bd = cls.get_project_details("serials", "novyy-kanal", "domik", "ua")
            add_candidate({
                "id": "teleportal_domik",
                "title": "Будиночок на щастя (Новий Канал)",
                "original_title": "Budynochok na schastya",
                "year": "2018–2026",
                "type": "series",
                "rating": "8.6",
                "poster": "https://teleportal.ua/storage/editor/fotos/domyk-na-schaste_1791280603145.jpg",
                "description": bd.get("description") or "Комедійний серіал Нового каналу про пригоди міської пари в селі Сеньківка.",
                "badges": ["🇺🇦 Новий Канал Оригінал"],
                "has_ukr": True,
                "has_ru": False,
                "source": "teleportal",
                "teleportal": {"type": "serials", "channel": "novyy-kanal", "project": "domik"}
            }, priority_bonus=25)

        # 3. Parallel external search: IMDb Suggest + Ru & Uk Wikipedia
        def search_imdb():
            try:
                enc = urllib.parse.quote(q_low)
                u = f"https://v3.sg.media-imdb.com/suggestion/x/{enc}.json"
                req = urllib.request.Request(u, headers={"User-Agent": USER_AGENT})
                with urllib.request.urlopen(req, timeout=3, context=_SSL_CTX) as r:
                    data = json.loads(r.read().decode('utf-8', errors='ignore'))
                out = []
                for d in data.get("d", [])[:5]:
                    imdb_id = d.get("id", "")
                    if not imdb_id.startswith("tt"):
                        continue
                    title = d.get("l", "")
                    year = str(d.get("y", ""))
                    qtype = d.get("q", "")
                    media_type = "series" if "TV" in str(d.get("qid", "")) or qtype in ("feature", "tv_series") else "movie"
                    img_obj = d.get("i", {})
                    img_url = img_obj.get("imageUrl", "") if isinstance(img_obj, dict) else ""
                    out.append({
                        "id": f"imdb_{imdb_id}",
                        "imdb_id": imdb_id,
                        "kp_id": "",
                        "title": title,
                        "original_title": title,
                        "year": year,
                        "type": media_type,
                        "rating": "IMDb",
                        "poster": img_url,
                        "description": "",
                        "badges": ["🇺🇦 Укр. озвучка", "🇷🇺 Рус", "🇬🇧 Orig"],
                        "has_ukr": True,
                        "has_ru": True,
                        "source": "imdb"
                    })
                return out
            except Exception:
                return []

        def search_wiki(lang_code="ru"):
            try:
                enc = urllib.parse.quote(q)
                w_url = f"https://{lang_code}.wikipedia.org/w/api.php?action=query&list=search&srsearch={enc}&format=json"
                req = urllib.request.Request(w_url, headers={"User-Agent": USER_AGENT})
                with urllib.request.urlopen(req, timeout=3, context=_SSL_CTX) as r:
                    wdata = json.loads(r.read().decode('utf-8', errors='ignore'))
                sr = wdata.get("query", {}).get("search", [])[:3]
                out = []
                for it in sr:
                    pid = it["pageid"]
                    raw_title = it["title"]
                    p_url = f"https://{lang_code}.wikipedia.org/w/api.php?action=query&prop=pageprops&ppprop=wikibase_item&pageids={pid}&format=json"
                    with urllib.request.urlopen(urllib.request.Request(p_url, headers={"User-Agent": USER_AGENT}), timeout=3, context=_SSL_CTX) as pr:
                        pdata = json.loads(pr.read().decode('utf-8', errors='ignore'))
                    w_item = pdata.get("query", {}).get("pages", {}).get(str(pid), {}).get("pageprops", {}).get("wikibase_item")
                    if not w_item:
                        continue
                    wd_url = f"https://www.wikidata.org/wiki/Special:EntityData/{w_item}.json"
                    with urllib.request.urlopen(urllib.request.Request(wd_url, headers={"User-Agent": USER_AGENT}), timeout=3, context=_SSL_CTX) as wr:
                        wd = json.loads(wr.read().decode('utf-8', errors='ignore'))
                    entity = wd.get("entities", {}).get(w_item, {})
                    claims = entity.get("claims", {})
                    kp = claims.get("P2603", [{}])[0].get("mainsnak", {}).get("datavalue", {}).get("value")
                    imdb = claims.get("P345", [{}])[0].get("mainsnak", {}).get("datavalue", {}).get("value")
                    if not (kp or imdb):
                        continue

                    labels = entity.get("labels", {})
                    title_uk = labels.get("uk", {}).get("value")
                    title_ru = labels.get("ru", {}).get("value")
                    title_en = labels.get("en", {}).get("value")
                    disp_title = title_uk or title_ru or re.sub(r'\s*\([^)]*\)', '', raw_title).strip()
                    
                    descs = entity.get("descriptions", {})
                    desc = descs.get("uk", {}).get("value") or descs.get("ru", {}).get("value") or ""
                    
                    # Year
                    year = ""
                    y_claim = claims.get("P577", [{}])[0].get("mainsnak", {}).get("datavalue", {}).get("value", {})
                    if isinstance(y_claim, dict) and "time" in y_claim:
                        m_y = re.search(r'([12]\d{3})', y_claim["time"])
                        if m_y:
                            year = m_y.group(1)

                    # Poster
                    img_f = claims.get("P18", [{}])[0].get("mainsnak", {}).get("datavalue", {}).get("value")
                    poster_url = ""
                    if img_f:
                        safe_fn = urllib.parse.quote(img_f.replace(" ", "_"))
                        import hashlib
                        m_hash = hashlib.md5(img_f.replace(" ", "_").encode('utf-8')).hexdigest()
                        poster_url = f"https://upload.wikimedia.org/wikipedia/commons/thumb/{m_hash[0]}/{m_hash[:2]}/{safe_fn}/400px-{safe_fn}"

                    # Type
                    media_type = "movie"
                    for p31 in claims.get("P31", []):
                        t_id = p31.get("mainsnak", {}).get("datavalue", {}).get("value", {}).get("id")
                        if t_id in ("Q5398426", "Q526877", "Q1259759", "Q581714"):
                            media_type = "series"

                    out.append({
                        "id": f"kp_{kp}" if kp else f"imdb_{imdb}",
                        "kp_id": str(kp) if kp else "",
                        "imdb_id": str(imdb) if imdb else "",
                        "title": disp_title,
                        "original_title": title_en or "",
                        "year": year,
                        "type": media_type,
                        "rating": "8.0",
                        "poster": poster_url,
                        "description": desc,
                        "badges": ["🇺🇦 Укр", "🇷🇺 Рус", "🇬🇧 Orig"],
                        "has_ukr": True,
                        "has_ru": True,
                        "source": "wiki"
                    })
                return out
            except Exception:
                return []

        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
                f_imdb = executor.submit(search_imdb)
                f_wru = executor.submit(search_wiki, "ru")
                f_wuk = executor.submit(search_wiki, "uk")
                for f in [f_wru, f_wuk, f_imdb]:
                    try:
                        for it in f.result(timeout=4):
                            add_candidate(it, priority_bonus=0)
                    except Exception:
                        pass
        except Exception:
            pass

        # Sort by score descending
        scored_results.sort(key=lambda x: x[0], reverse=True)

        # If user searched a multi-word specific title (e.g. "Губка боб в бегах"),
        # keep only the top relevant results instead of showing unrelated franchise items!
        if scored_results and len(q_words) >= 3:
            top_score = scored_results[0][0]
            scored_results = [s for s in scored_results if s[0] >= top_score - 10]

        final_list = [s[1] for s in scored_results][:limit]
        set_cache(cache_key, final_list, ttl=1800)
        return final_list

    @classmethod
    def get_media_details(cls, kp_id: Optional[str] = None, imdb_id: Optional[str] = None, force_fresh: bool = False) -> Dict[str, Any]:
        kp_id = str(kp_id or "").strip()
        imdb_id = str(imdb_id or "").strip()
        if not (kp_id or imdb_id):
            return {"error": "Missing kp_id or imdb_id"}

        cache_key = f"media_details_{kp_id}_{imdb_id}"
        if not force_fresh:
            cached = get_cache(cache_key)
            if cached:
                return cached

        candidate_urls = []
        if imdb_id and imdb_id.startswith("tt"):
            candidate_urls.append(f"https://api.namy.ws/embed/imdb/{imdb_id}")
        if kp_id and kp_id.isdigit():
            candidate_urls.append(f"https://api.namy.ws/embed/kp/{kp_id}")
        if not candidate_urls:
            if imdb_id: candidate_urls.append(f"https://api.namy.ws/embed/imdb/{imdb_id}")
            if kp_id: candidate_urls.append(f"https://api.namy.ws/embed/kp/{kp_id}")

        html = None
        for u in candidate_urls:
            try:
                req = urllib.request.Request(u, headers={"User-Agent": USER_AGENT, "Referer": "https://api.namy.ws/"})
                with urllib.request.urlopen(req, timeout=6, context=_SSL_CTX) as r:
                    res_body = r.read().decode('utf-8', errors='ignore')
                    if "makePlayer" in res_body:
                        html = res_body
                        break
            except Exception:
                continue

        if not html:
            return {"error": "Поток видео не найден на видеобалансере"}

        mp = re.search(r'makePlayer\((\{.*?\}\));', html, re.DOTALL)
        if not mp:
            return {"error": "Stream player signature not found in upstream source"}

        blob = mp.group(1)
        title_m = re.search(r'title\s*:\s*["\']([^"\']+)["\']', blob)
        main_title = title_m.group(1) if title_m else "Видео"

        # Check if TV Series
        if "seasons:" in blob or "playlist:" in blob:
            idx = blob.find("seasons:[")
            if idx == -1:
                idx = blob.find("seasons: [")
            if idx != -1:
                start = blob.find("[", idx)
                bracket_count = 0
                end = -1
                for i in range(start, len(blob)):
                    if blob[i] == "[":
                        bracket_count += 1
                    elif blob[i] == "]":
                        bracket_count -= 1
                        if bracket_count == 0:
                            end = i + 1
                            break
                if end != -1:
                    seasons_raw = json.loads(blob[start:end])
                    seasons = []
                    has_ukr = False
                    has_ru = False
                    all_dub_names = set()

                    for s in seasons_raw:
                        s_num = s.get("season")
                        episodes = []
                        for ep in s.get("episodes", []):
                            audio_raw = ep.get("audio", {})
                            names = audio_raw.get("names", [])
                            audio_list = []
                            for idx_a, a_name in enumerate(names):
                                lang = detect_audio_lang(a_name)
                                if lang == "uk":
                                    has_ukr = True
                                elif lang == "ru":
                                    has_ru = True
                                all_dub_names.add(a_name)
                                audio_list.append({
                                    "index": idx_a,
                                    "name": a_name,
                                    "lang": lang,
                                    "flag": "🇺🇦" if lang == "uk" else "🇷🇺" if lang == "ru" else "🇬🇧"
                                })
                            episodes.append({
                                "episode": ep.get("episode"),
                                "title": ep.get("title") or f"Серия {ep.get('episode')}",
                                "hls": ep.get("hls", ""),
                                "audio": audio_list,
                                "duration": ep.get("duration", 0),
                                "poster": ep.get("poster", "")
                            })
                        seasons.append({
                            "season": s_num,
                            "episodes": episodes
                        })

                    res = {
                        "type": "series",
                        "title": main_title,
                        "kp_id": kp_id,
                        "imdb_id": imdb_id,
                        "seasons": seasons,
                        "has_ukr": has_ukr,
                        "has_ru": has_ru,
                        "available_dubs": list(all_dub_names)
                    }
                    set_cache(cache_key, res, ttl=3600)
                    return res

        # Single Movie
        hls_m = re.search(r'hls\s*:\s*["\']([^"\']+)["\']', blob)
        audio_m = re.search(r'audio\s*:\s*(\{.*?\})', blob)
        cc_m = re.search(r'cc\s*:\s*(\[.*?\])', blob)

        hls_url = hls_m.group(1) if hls_m else ""
        audio_list = []
        has_ukr = False
        has_ru = False
        if audio_m:
            try:
                adata = json.loads(audio_m.group(1))
                for idx_a, a_name in enumerate(adata.get("names", [])):
                    lang = detect_audio_lang(a_name)
                    if lang == "uk":
                        has_ukr = True
                    elif lang == "ru":
                        has_ru = True
                    audio_list.append({
                        "index": idx_a,
                        "name": a_name,
                        "lang": lang,
                        "flag": "🇺🇦" if lang == "uk" else "🇷🇺" if lang == "ru" else "🇬🇧"
                    })
            except Exception:
                pass

        subtitles = []
        if cc_m:
            try:
                subtitles = json.loads(cc_m.group(1))
            except Exception:
                pass

        res = {
            "type": "movie",
            "title": main_title,
            "kp_id": kp_id,
            "imdb_id": imdb_id,
            "hls": hls_url,
            "audio": audio_list,
            "subtitles": subtitles,
            "has_ukr": has_ukr,
            "has_ru": has_ru
        }
        set_cache(cache_key, res, ttl=3600)
        return res

    @classmethod
    def resolve_stream_for_play(cls, kp_id: Optional[str] = None, imdb_id: Optional[str] = None, season: Optional[int] = None, episode: Optional[str] = None) -> Dict[str, Any]:
        # Always obtain a fresh signed embed token to prevent 410 Gone / expired token errors
        details = cls.get_media_details(kp_id=kp_id, imdb_id=imdb_id, force_fresh=True)
        if details.get("error"):
            return {"type": "none", "url": "", "error": details["error"]}

        if details.get("type") == "movie":
            raw_hls = details.get("hls", "")
            proxied_hls = f"/api/hls/proxy?url={urllib.parse.quote(raw_hls, safe='')}" if raw_hls else ""
            return {
                "type": "hls",
                "url": proxied_hls,
                "raw_url": raw_hls,
                "title": details.get("title", "Фильм"),
                "audio_tracks": details.get("audio", []),
                "subtitles": details.get("subtitles", []),
                "has_ukr": details.get("has_ukr", False),
                "has_ru": details.get("has_ru", False),
                "source": "collaps_hls"
            }
        elif details.get("type") == "series":
            seasons = details.get("seasons", [])
            target_season = None
            if season is not None:
                for s in seasons:
                    if str(s.get("season")) == str(season):
                        target_season = s
                        break
            if not target_season and seasons:
                target_season = seasons[0]

            target_episode = None
            if target_season:
                eps = target_season.get("episodes", [])
                if episode is not None:
                    for ep in eps:
                        if str(ep.get("episode")) == str(episode):
                            target_episode = ep
                            break
                if not target_episode and eps:
                    target_episode = eps[0]

            if target_episode:
                ep_title = f"{details.get('title', 'Сериал')} (Сезон {target_season.get('season')}, Серия {target_episode.get('episode')})"
                raw_hls = target_episode.get("hls", "")
                proxied_hls = f"/api/hls/proxy?url={urllib.parse.quote(raw_hls, safe='')}" if raw_hls else ""
                return {
                    "type": "hls",
                    "url": proxied_hls,
                    "raw_url": raw_hls,
                    "title": ep_title,
                    "audio_tracks": target_episode.get("audio", []),
                    "duration": target_episode.get("duration", 0),
                    "poster": target_episode.get("poster", ""),
                    "season": target_season.get("season"),
                    "episode": target_episode.get("episode"),
                    "source": "collaps_hls"
                }

        return {"type": "none", "url": "", "error": "Could not extract stream"}

def clean_text(v: Any, limit: int = 100) -> str:
    return str(v or "").strip()[:limit]
