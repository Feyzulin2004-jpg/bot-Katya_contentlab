# -*- coding: utf-8 -*-
import glob
import json
import logging
import os
import shutil
import struct
import subprocess
import threading
import time
import unicodedata

from telegram import InputFile, InputMediaPhoto
from telegram.error import NetworkError, RetryAfter, TimedOut

from bot.config import DATA_DIR, MEDIA_DIR

log = logging.getLogger(__name__)
CACHE_PATH = os.path.join(DATA_DIR, "tg_file_ids.json")
PREPARED_DIR = os.path.join(DATA_DIR, "prepared_video")
PREPARE_SCRIPT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "deploy", "prepare_videos.sh")
UPLOAD_TIMEOUT = 180
HEVC = ("hvc1", "hev1", "hevC")
PREPARE_VERSION = "v3"
_ffmpeg_gate = threading.Lock()
_converting = {}
_converting_lock = threading.Lock()


def _send_keyboard(bot, chat_id, reply_markup):
    if not reply_markup:
        return
    bot.send_message(chat_id, "\u2060", reply_markup=reply_markup)


def _iter_mp4_boxes(fh, end):
    while fh.tell() + 8 <= end:
        start = fh.tell()
        hdr = fh.read(8)
        if len(hdr) < 8:
            break
        size, typ = struct.unpack(">I4s", hdr)
        hdr_len = 8
        if size == 1:
            large = fh.read(8)
            if len(large) < 8:
                break
            size = struct.unpack(">Q", large)[0]
            hdr_len = 16
        elif size == 0:
            size = end - start
        if size < hdr_len:
            break
        yield start, size, typ, hdr_len
        fh.seek(start + size)


def video_info(path):
    width = height = None
    codec = None
    duration = None
    video_codecs = {b"hvc1", b"hev1", b"avc1", b"avc3", b"mp4v", b"vp09"}
    try:
        size = os.path.getsize(path)
        with open(path, "rb") as fh:
            def walk(end):
                nonlocal width, height, codec, duration
                for start, box_size, typ, hdr_len in _iter_mp4_boxes(fh, end):
                    payload_start = start + hdr_len
                    box_end = start + box_size
                    if typ in (b"moov", b"trak", b"mdia", b"minf", b"stbl"):
                        fh.seek(payload_start)
                        walk(box_end)
                    elif typ == b"tkhd":
                        fh.seek(payload_start)
                        payload = fh.read(min(box_end - payload_start, 96))
                        if payload:
                            ver = payload[0]
                            off = 76 if ver == 0 else 88
                            if len(payload) >= off + 8:
                                w = struct.unpack(">I", payload[off:off + 4])[0] / 65536.0
                                h = struct.unpack(">I", payload[off + 4:off + 8])[0] / 65536.0
                                if w >= 2 and h >= 2:
                                    width, height = w, h
                    elif typ == b"mdhd":
                        fh.seek(payload_start)
                        payload = fh.read(min(box_end - payload_start, 32))
                        if payload:
                            ver = payload[0]
                            ts = dur = 0
                            if ver == 0 and len(payload) >= 20:
                                ts = struct.unpack(">I", payload[12:16])[0]
                                dur = struct.unpack(">I", payload[16:20])[0]
                            elif ver == 1 and len(payload) >= 32:
                                ts = struct.unpack(">I", payload[20:24])[0]
                                dur = struct.unpack(">Q", payload[24:32])[0]
                            if ts:
                                seconds = int(round(float(dur) / ts))
                                if seconds > (duration or 0):
                                    duration = seconds
                    elif typ == b"stsd" and codec is None:
                        fh.seek(payload_start)
                        payload = fh.read(min(20, box_end - payload_start))
                        if len(payload) >= 16:
                            fourcc = payload[12:16]
                            if fourcc in video_codecs:
                                codec = fourcc.decode("latin1")
                    fh.seek(box_end)

            walk(size)
    except Exception:
        log.exception("Не прочитать метаданные %s", path)
    return (
        int(width) if width else None,
        int(height) if height else None,
        codec,
        duration,
    )


def _video_stamp(path):
    return "{}|{}|{}|{}".format(
        PREPARE_VERSION,
        os.path.abspath(path),
        os.path.getsize(path),
        int(os.path.getmtime(path)),
    )


def _prepared_dest(path):
    os.makedirs(PREPARED_DIR, exist_ok=True)
    return os.path.join(PREPARED_DIR, os.path.splitext(os.path.basename(path))[0] + ".mp4")


def _prepared_ok(path):
    dest = _prepared_dest(path)
    stamp_path = dest + ".src"
    if not (os.path.isfile(dest) and os.path.isfile(stamp_path)):
        return None
    try:
        with open(stamp_path, "r", encoding="utf-8") as fh:
            if fh.read().strip() != _video_stamp(path):
                return None
    except Exception:
        return None
    return dest


def _convert_sync(path):
    if _prepared_ok(path):
        return
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        return
    dest = _prepared_dest(path)
    script = PREPARE_SCRIPT
    with _ffmpeg_gate:
        if _prepared_ok(path):
            return
        log.info("Перекодирую %s (HEVC) в H.264 для Telegram", os.path.basename(path))
        try:
            if os.path.isfile(script) and shutil.which("bash"):
                subprocess.check_call(["bash", script, path], timeout=600)
                return
        except Exception:
            log.exception("Скрипт подготовки не смог %s, пробую ffmpeg напрямую", os.path.basename(path))
        tmp = dest + ".part.mp4"
        vf = (
            "scale=w='min(1080,iw)':h='min(1080,ih)':force_original_aspect_ratio=decrease,"
            "scale=trunc(iw/2)*2:trunc(ih/2)*2,fps=30,format=yuv420p"
        )
        ok = False
        for extra in (["-c:a", "aac", "-ac", "2", "-ar", "44100", "-b:a", "160k"], ["-an"]):
            cmd = [
                ffmpeg, "-y", "-i", path,
                "-vf", vf,
                "-c:v", "libx264", "-profile:v", "high", "-level", "4.1",
                "-pix_fmt", "yuv420p", "-preset", "medium", "-crf", "20",
            ] + extra + [
                "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709",
                "-movflags", "+faststart", "-tag:v", "avc1",
                tmp,
            ]
            try:
                subprocess.check_call(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=600)
                ok = True
                break
            except Exception:
                log.warning("ffmpeg не прошёл (%s) для %s", extra[0], os.path.basename(path))
        if not ok:
            log.error("Не удалось перекодировать %s", path)
            if os.path.isfile(tmp):
                try:
                    os.remove(tmp)
                except OSError:
                    pass
            return
        os.replace(tmp, dest)
        with open(dest + ".src", "w", encoding="utf-8") as fh:
            fh.write(_video_stamp(path))
        _make_thumb(dest)


def _make_thumb(path):
    dest = path + ".jpg"
    if os.path.isfile(dest) and os.path.getsize(dest) > 200:
        return dest
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        return None
    try:
        subprocess.check_call(
            [ffmpeg, "-y", "-ss", "0.4", "-i", path, "-frames:v", "1", "-q:v", "5", dest],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=30,
        )
        if os.path.isfile(dest) and os.path.getsize(dest) > 200:
            return dest
    except Exception:
        log.warning("Не сделала превью для %s", os.path.basename(path))
    return None


def prepare_video(path):
    width, height, codec, duration = video_info(path)
    if (codec or "") in HEVC:
        if shutil.which("ffmpeg"):
            _convert_sync(path)
        ready = _prepared_ok(path)
        if ready:
            w2, h2, c2, d2 = video_info(ready)
            return ready, w2 or width, h2 or height, d2 or duration, True
        return path, width, height, duration, False
    return path, width, height, duration, True


def prepare_all_videos():
    if not shutil.which("ffmpeg"):
        log.info("ffmpeg нет, видео оставлю как есть")
        return
    for dirpath, _, files in os.walk(MEDIA_DIR):
        for name in files:
            if os.path.splitext(name)[1].lower() not in (".mov", ".mp4"):
                continue
            path = os.path.join(dirpath, name)
            _, _, codec, _ = video_info(path)
            if (codec or "") in HEVC and not _prepared_ok(path):
                _convert_sync(path)
    log.info("Подготовка видео закончена")


def _cache_load():
    try:
        with open(CACHE_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _cache_save(data):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=0)


def _cache_key(path):
    st = os.stat(path)
    return "{}|{}|{}".format(os.path.abspath(path), st.st_size, int(st.st_mtime))


def cached_id(path):
    return _cache_load().get(_cache_key(path))


def store_id(path, file_id):
    if not file_id:
        return
    data = _cache_load()
    data[_cache_key(path)] = file_id
    _cache_save(data)


def _abs(*parts):
    return os.path.join(MEDIA_DIR, *parts)


def existing(path):
    return path if path and os.path.isfile(path) else None


def glob_existing(pattern):
    return [p for p in sorted(glob.glob(pattern)) if os.path.isfile(p)]


def read_text(*parts):
    path = _abs(*parts)
    if os.path.isfile(path):
        with open(path, "r", encoding="utf-8") as f:
            text = f.read().strip()
            if text:
                return text
    return None


def _fold(text):
    text = unicodedata.normalize("NFKD", text or "").lower()
    return "".join(ch for ch in text if not unicodedata.combining(ch))


def _prompt_name(kind):
    return {"price": "price", "stories": "stories", "carousel": "carousel"}.get(kind, "stories")


def find_prompt_doc(kind):
    folder = _abs("prompts")
    if not os.path.isdir(folder):
        return None
    keys = {
        "price": ("праис", "price"),
        "stories": ("сторис", "stories"),
        "carousel": ("карусел", "carousel"),
    }.get(kind, ("сторис", "stories"))
    keys = [_fold(k) for k in keys]
    found = []
    for name in os.listdir(folder):
        low = name.lower()
        if not (low.endswith(".docx") or low.endswith(".doc")):
            continue
        folded = _fold(name)
        if any(k in folded for k in keys):
            found.append(os.path.join(folder, name))
    found.sort()
    return found[0] if found else None


def _fill_video_kwargs(kwargs, path, width, height, duration):
    if width and height:
        kwargs["width"] = int(width)
        kwargs["height"] = int(height)
    if duration:
        kwargs["duration"] = int(duration)
    thumb = _make_thumb(path)
    if thumb:
        return open(thumb, "rb")
    return None


def send_video(bot, chat_id, *rel, caption=None):
    path = existing(_abs(*rel))
    if not path:
        return False
    path, width, height, duration, inline = prepare_video(path)
    if not inline:
        return send_document_path(bot, chat_id, path)
    kwargs = {"caption": caption, "supports_streaming": True, "timeout": UPLOAD_TIMEOUT}
    thumb_fh = _fill_video_kwargs(kwargs, path, width, height, duration)
    fh = open(path, "rb")
    try:
        bot.send_video(
            chat_id,
            video=InputFile(fh, filename=os.path.splitext(os.path.basename(path))[0] + ".mp4"),
            **kwargs
        )
    finally:
        fh.close()
        if thumb_fh:
            thumb_fh.close()
    return True


def send_document_path(bot, chat_id, path, filename=None):
    if not existing(path):
        return False
    fh = open(path, "rb")
    try:
        bot.send_document(
            chat_id,
            document=InputFile(fh, filename=filename or os.path.basename(path)),
        )
    finally:
        fh.close()
    return True


def send_document(bot, chat_id, *rel, filename=None):
    return send_document_path(bot, chat_id, _abs(*rel), filename=filename)


def send_prompt_video(bot, chat_id, kind):
    if kind == "carousel":
        return send_named(bot, chat_id, "IMG_9835", caption="Как это работает 👆")
    name = _prompt_name(kind)
    for rel in (
        ("prompts", "{}.mp4".format(name)),
        ("prompts", "{}.mov".format(name)),
        ("prompts", "{}.MP4".format(name)),
        ("prompts", "{}.MOV".format(name)),
        ("instruction.mp4",),
        ("instruction.MOV",),
    ):
        if send_video(bot, chat_id, *rel, caption="Как пользоваться промтом 👆"):
            return True
    return False


def send_prompt_doc(bot, chat_id, kind):
    path = find_prompt_doc(kind)
    if path:
        return send_document_path(bot, chat_id, path, filename=os.path.basename(path))
    name = _prompt_name(kind)
    title = {"price": "прайса", "stories": "сторис", "carousel": "дизайна карусели"}.get(name, "сторис")
    for ext in ("docx", "doc", "txt"):
        filename = "Промт для {}.{}".format(title, ext)
        if send_document(bot, chat_id, "prompts", "{}.{}".format(name, ext), filename=filename):
            return True
    return False


def send_photos(bot, chat_id, paths, caption=None):
    files = [p for p in paths if existing(p)]
    if not files:
        log.info("Нет файлов для отправки: %s", paths)
        return False
    if len(files) == 1:
        with open(files[0], "rb") as f:
            bot.send_photo(chat_id, photo=f, caption=caption)
        return True
    media = []
    opened = []
    try:
        for i, path in enumerate(files[:10]):
            fh = open(path, "rb")
            opened.append(fh)
            media.append(InputMediaPhoto(media=fh, caption=caption if i == 0 else None))
        bot.send_media_group(chat_id, media=media)
    finally:
        for fh in opened:
            fh.close()
    return True


def album(folder):
    base = _abs(folder)
    files = []
    for ext in ("*.jpg", "*.jpeg", "*.png", "*.webp"):
        files.extend(glob_existing(os.path.join(base, ext)))
    return files


def videos(folder):
    base = _abs(folder)
    files = []
    for ext in ("*.mp4", "*.mov", "*.webm", "*.MP4", "*.MOV"):
        files.extend(glob_existing(os.path.join(base, ext)))
    return files


def documents(folder):
    base = _abs(folder)
    files = []
    for ext in ("*.pdf", "*.txt", "*.docx", "*.doc", "*.xlsx"):
        files.extend(glob_existing(os.path.join(base, ext)))
    return files


def send_folder(bot, chat_id, folder, caption=None):
    sent = False
    vid_list = videos(folder)
    for i, src in enumerate(vid_list):
        path, width, height, duration, inline = prepare_video(src)
        caption_i = caption if (i == 0 and not album(folder)) else None
        if not inline:
            send_document_path(bot, chat_id, path)
            sent = True
            continue
        kwargs = {
            "caption": caption_i,
            "supports_streaming": True,
            "timeout": UPLOAD_TIMEOUT,
        }
        thumb_fh = _fill_video_kwargs(kwargs, path, width, height, duration)
        with open(path, "rb") as f:
            try:
                bot.send_video(
                    chat_id,
                    video=InputFile(f, filename=os.path.splitext(os.path.basename(path))[0] + ".mp4"),
                    **kwargs
                )
            finally:
                if thumb_fh:
                    thumb_fh.close()
        sent = True
    photos = album(folder)
    if photos:
        send_photos(bot, chat_id, photos, caption=caption if not sent else None)
        sent = True
    for path in documents(folder):
        with open(path, "rb") as f:
            bot.send_document(chat_id, document=InputFile(f, filename=os.path.basename(path)))
        sent = True
    return sent


def find_named(stem):
    stem = (stem or "").upper()
    if not stem:
        return None
    exact = []
    prefix = []
    for dirpath, _, files in os.walk(MEDIA_DIR):
        for name in files:
            base, ext = os.path.splitext(name)
            path = os.path.join(dirpath, name)
            if base.upper() == stem:
                exact.append(path)
            elif name.upper().startswith(stem):
                prefix.append(path)
    pool = exact or prefix
    if not pool:
        return None

    def rank(path):
        ext = os.path.splitext(path)[1].lower()
        if ext in (".mp4", ".mov", ".webm"):
            return 0
        if ext in (".jpg", ".jpeg", ".png", ".webp"):
            return 2
        return 1

    pool.sort(key=rank)
    return pool[0]


def send_named(bot, chat_id, stem, caption=None, reply_markup=None):
    path = find_named(stem)
    if not path:
        log.info("Нет файла %s", stem)
        return False
    ext = os.path.splitext(path)[1].lower()
    cap = caption if caption and len(caption) <= 1024 else None
    kind = "video" if ext in (".mp4", ".mov", ".webm") else (
        "photo" if ext in (".jpg", ".jpeg", ".png", ".webp") else "document"
    )
    try:
        _send_media(bot, chat_id, path, kind, cap, reply_markup if cap else None)
    except Exception:
        log.exception("Не удалось отправить %s", stem)
        if caption:
            bot.send_message(
                chat_id,
                caption + "\n\n(файл не загрузился, слишком тяжёлый или сеть оборвалась)",
                reply_markup=reply_markup,
                disable_web_page_preview=True,
            )
            return False
        raise
    if caption and not cap:
        bot.send_message(
            chat_id,
            caption,
            reply_markup=reply_markup,
            disable_web_page_preview=True,
        )
    elif reply_markup and not cap:
        _send_keyboard(bot, chat_id, reply_markup)
    return True


def _send_media(bot, chat_id, path, kind, caption=None, reply_markup=None):
    width = height = duration = None
    if kind == "video":
        path, width, height, duration, inline = prepare_video(path)
        if not inline:
            kind = "document"
    file_id = None if path.lower().endswith(".mov") else cached_id(path)
    last_error = None
    for attempt in range(3):
        try:
            payload = file_id
            fh = None
            thumb_fh = None
            if not payload:
                fh = open(path, "rb")
                filename = os.path.basename(path)
                if kind == "video":
                    filename = os.path.splitext(filename)[0] + ".mp4"
                payload = InputFile(fh, filename=filename)
            try:
                if kind == "video":
                    kwargs = {
                        "caption": caption,
                        "supports_streaming": True,
                        "reply_markup": reply_markup,
                        "timeout": UPLOAD_TIMEOUT,
                    }
                    thumb_fh = _fill_video_kwargs(kwargs, path, width, height, duration)
                    msg = bot.send_video(chat_id, video=payload, **kwargs)
                    new_id = msg.video.file_id if msg.video else None
                elif kind == "photo":
                    msg = bot.send_photo(
                        chat_id,
                        photo=payload,
                        caption=caption,
                        reply_markup=reply_markup,
                        timeout=UPLOAD_TIMEOUT,
                    )
                    new_id = None
                    if msg.photo:
                        new_id = msg.photo[-1].file_id
                else:
                    msg = bot.send_document(
                        chat_id,
                        document=payload,
                        caption=caption,
                        reply_markup=reply_markup,
                        timeout=UPLOAD_TIMEOUT,
                    )
                    new_id = msg.document.file_id if msg.document else None
            finally:
                if fh:
                    fh.close()
                if thumb_fh:
                    thumb_fh.close()
            if new_id and not file_id:
                store_id(path, new_id)
            return msg
        except RetryAfter as exc:
            last_error = exc
            time.sleep(int(getattr(exc, "retry_after", 5)) + 1)
        except (TimedOut, NetworkError) as exc:
            last_error = exc
            log.warning("Повтор загрузки %s (%s)", os.path.basename(path), exc)
            time.sleep(3 * (attempt + 1))
            file_id = None
    if last_error:
        raise last_error
    return None


def send_stems(bot, chat_id, stems, caption=None, reply_markup=None):
    stems = [s for s in (stems or []) if s]
    if len(stems) <= 1:
        return send_named(bot, chat_id, stems[0] if stems else "", caption=caption, reply_markup=reply_markup)
    paths = []
    for stem in stems:
        path = find_named(stem)
        if path:
            paths.append(path)
    if not paths:
        if caption:
            bot.send_message(chat_id, caption, reply_markup=reply_markup, disable_web_page_preview=True)
        return False
    opened = []
    try:
        media = []
        for i, path in enumerate(paths[:10]):
            fh = open(path, "rb")
            opened.append(fh)
            media.append(InputMediaPhoto(media=fh, caption=caption if i == 0 else None))
        bot.send_media_group(chat_id, media=media, timeout=UPLOAD_TIMEOUT)
    finally:
        for fh in opened:
            fh.close()
    if reply_markup:
        bot.send_message(chat_id, "👇", reply_markup=reply_markup, disable_web_page_preview=True)
    return True


def send_named_many(bot, chat_id, stems, caption=None, reply_markup=None):
    stems = [s for s in (stems or []) if s]
    if not stems:
        if caption:
            bot.send_message(
                chat_id,
                caption,
                reply_markup=reply_markup,
                disable_web_page_preview=True,
            )
        return False
    if len(stems) == 1:
        return send_named(bot, chat_id, stems[0], caption=caption, reply_markup=reply_markup)
    paths = []
    for stem in stems:
        path = find_named(stem)
        if path:
            paths.append(path)
    if not paths:
        if caption:
            bot.send_message(
                chat_id,
                caption,
                reply_markup=reply_markup,
                disable_web_page_preview=True,
            )
        return False
    photo_ext = (".jpg", ".jpeg", ".png", ".webp")
    photos = [p for p in paths if os.path.splitext(p)[1].lower() in photo_ext]
    others = [p for p in paths if p not in photos]
    for path in others:
        send_named(bot, chat_id, os.path.splitext(os.path.basename(path))[0], caption=None)
    if photos:
        if len(photos) == 1:
            fh = open(photos[0], "rb")
            try:
                bot.send_photo(chat_id, photo=fh, timeout=UPLOAD_TIMEOUT)
            finally:
                fh.close()
        else:
            media = []
            opened = []
            try:
                for path in photos[:10]:
                    fh = open(path, "rb")
                    opened.append(fh)
                    media.append(InputMediaPhoto(media=fh))
                bot.send_media_group(chat_id, media=media)
            finally:
                for fh in opened:
                    fh.close()
    if caption:
        bot.send_message(
            chat_id,
            caption,
            reply_markup=reply_markup,
            disable_web_page_preview=True,
        )
    elif reply_markup:
        _send_keyboard(bot, chat_id, reply_markup)
    return True
