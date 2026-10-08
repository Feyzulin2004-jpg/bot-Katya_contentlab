# -*- coding: utf-8 -*-
import json
import os
import sqlite3
import threading
import time

from bot.config import DATA_DIR, DB_PATH

_local = threading.local()


def _conn():
    conn = getattr(_local, "conn", None)
    if conn is None:
        os.makedirs(DATA_DIR, exist_ok=True)
        conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=30)
        conn.row_factory = sqlite3.Row
        _local.conn = conn
    return conn


def init_db():
    conn = _conn()
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            source TEXT,
            segment TEXT,
            tags_json TEXT NOT NULL DEFAULT '[]',
            paid INTEGER NOT NULL DEFAULT 0,
            blocked INTEGER NOT NULL DEFAULT 0,
            waiting_question INTEGER NOT NULL DEFAULT 0,
            created_at INTEGER NOT NULL,
            updated_at INTEGER NOT NULL
        );

        CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            kind TEXT NOT NULL,
            eta INTEGER NOT NULL,
            payload TEXT,
            status TEXT NOT NULL DEFAULT 'pending',
            created_at INTEGER NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_jobs_due ON jobs (status, eta);
        CREATE INDEX IF NOT EXISTS idx_jobs_user ON jobs (user_id, kind, status);

        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
        """
    )
    cols = [r[1] for r in conn.execute("PRAGMA table_info(users)")]
    if "drip_step" not in cols:
        conn.execute("ALTER TABLE users ADD COLUMN drip_step INTEGER NOT NULL DEFAULT 0")
    if "last_payment_id" not in cols:
        conn.execute("ALTER TABLE users ADD COLUMN last_payment_id TEXT")
    conn.commit()


def upsert_user(user_id, username=None, first_name=None, source=None):
    now = int(time.time())
    conn = _conn()
    row = conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()
    if row is None:
        conn.execute(
            """
            INSERT INTO users (user_id, username, first_name, source, tags_json, created_at, updated_at)
            VALUES (?, ?, ?, ?, '[]', ?, ?)
            """,
            (user_id, username, first_name, source, now, now),
        )
        conn.commit()
        return get_user(user_id)
    fields = {"updated_at": now}
    if username is not None:
        fields["username"] = username
    if first_name is not None:
        fields["first_name"] = first_name
    if source and not row["source"]:
        fields["source"] = source
    sets = ", ".join(k + " = ?" for k in fields)
    conn.execute(
        "UPDATE users SET " + sets + " WHERE user_id = ?",
        list(fields.values()) + [user_id],
    )
    conn.commit()
    return get_user(user_id)


def get_user(user_id):
    row = _conn().execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()
    return dict(row) if row else None


def get_setting(key, default=""):
    row = _conn().execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
    if not row:
        return default
    return row["value"]


def set_setting(key, value):
    _conn().execute(
        "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
        (key, "" if value is None else str(value)),
    )
    _conn().commit()


def set_fields(user_id, **fields):
    if not fields:
        return
    fields["updated_at"] = int(time.time())
    sets = ", ".join(k + " = ?" for k in fields)
    _conn().execute(
        "UPDATE users SET " + sets + " WHERE user_id = ?",
        list(fields.values()) + [user_id],
    )
    _conn().commit()


def get_tags(user_id):
    user = get_user(user_id)
    if not user:
        return []
    try:
        return json.loads(user["tags_json"] or "[]")
    except ValueError:
        return []


def add_tag(user_id, tag):
    tags = get_tags(user_id)
    if tag not in tags:
        tags.append(tag)
        set_fields(user_id, tags_json=json.dumps(tags, ensure_ascii=False))
    return tags


def has_tag(user_id, tag):
    return tag in get_tags(user_id)


def mark_paid(user_id):
    add_tag(user_id, "paid")
    set_fields(user_id, paid=1)
    cancel_user_jobs(user_id)


def mark_blocked(user_id, blocked=True):
    set_fields(user_id, blocked=1 if blocked else 0)


def schedule_job(user_id, kind, delay_seconds, payload=None, replace=True):
    conn = _conn()
    if replace:
        conn.execute(
            "UPDATE jobs SET status = 'cancelled' WHERE user_id = ? AND kind = ? AND status = 'pending'",
            (user_id, kind),
        )
    now = int(time.time())
    conn.execute(
        """
        INSERT INTO jobs (user_id, kind, eta, payload, status, created_at)
        VALUES (?, ?, ?, ?, 'pending', ?)
        """,
        (user_id, kind, now + int(delay_seconds), payload, now),
    )
    conn.commit()


def cancel_kind(kind):
    _conn().execute(
        "UPDATE jobs SET status = 'cancelled' WHERE kind = ? AND status = 'pending'",
        (kind,),
    )
    _conn().commit()


def cancel_user_jobs(user_id, kinds=None):
    conn = _conn()
    if kinds:
        q = ",".join("?" * len(kinds))
        conn.execute(
            "UPDATE jobs SET status = 'cancelled' WHERE user_id = ? AND status = 'pending' AND kind IN ("
            + q
            + ")",
            [user_id] + list(kinds),
        )
    else:
        conn.execute(
            "UPDATE jobs SET status = 'cancelled' WHERE user_id = ? AND status = 'pending'",
            (user_id,),
        )
    conn.commit()


def due_jobs(limit=50):
    now = int(time.time())
    return [
        dict(r)
        for r in _conn()
        .execute(
            """
            SELECT * FROM jobs
            WHERE status = 'pending' AND eta <= ?
            ORDER BY eta ASC
            LIMIT ?
            """,
            (now, limit),
        )
        .fetchall()
    ]


def finish_job(job_id, status="done"):
    _conn().execute("UPDATE jobs SET status = ? WHERE id = ?", (status, job_id))
    _conn().commit()


def stats():
    from bot.config import ADMIN_IDS

    conn = _conn()
    if ADMIN_IDS:
        skip = "user_id NOT IN ({})".format(",".join("?" * len(ADMIN_IDS)))
        args = list(ADMIN_IDS)
    else:
        skip = "1=1"
        args = []
    total = conn.execute("SELECT COUNT(*) FROM users WHERE " + skip, args).fetchone()[0]
    paid = conn.execute(
        "SELECT COUNT(*) FROM users WHERE paid = 1 AND " + skip, args
    ).fetchone()[0]
    sources = conn.execute(
        "SELECT source, COUNT(*) as c FROM users WHERE " + skip + " GROUP BY source", args
    ).fetchall()
    paid_sources = conn.execute(
        "SELECT source, COUNT(*) as c FROM users WHERE paid = 1 AND " + skip + " GROUP BY source",
        args,
    ).fetchall()
    segments = conn.execute(
        "SELECT segment, COUNT(*) as c FROM users WHERE segment IS NOT NULL AND segment != '' AND "
        + skip
        + " GROUP BY segment",
        args,
    ).fetchall()
    return {
        "total": total,
        "paid": paid,
        "sources": {r["source"] or "": r["c"] for r in sources},
        "paid_sources": {r["source"] or "": r["c"] for r in paid_sources},
        "segments": {r["segment"] or "": r["c"] for r in segments},
    }


def list_users(limit=50):
    return [
        dict(r)
        for r in _conn()
        .execute(
            "SELECT user_id, username, first_name, source, segment, paid, tags_json FROM users ORDER BY created_at DESC LIMIT ?",
            (limit,),
        )
        .fetchall()
    ]
