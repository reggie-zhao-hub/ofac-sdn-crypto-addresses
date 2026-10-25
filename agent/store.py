# -*- coding: utf-8 -*-
"""agent/store.py —— SQLite 存档与差异计算"""
import sqlite3, uuid
from datetime import datetime, timezone
from . import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS run (
    run_id       TEXT PRIMARY KEY,
    captured_at  TEXT,
    source_sha   TEXT,
    n_addresses  INTEGER,
    status       TEXT,
    note         TEXT
);
CREATE TABLE IF NOT EXISTS snapshot (
    run_id     TEXT,
    address    TEXT,
    currency   TEXT,
    entity     TEXT,
    fixed_ref  TEXT
);
CREATE INDEX IF NOT EXISTS idx_snap_run ON snapshot(run_id);
"""


def _conn():
    c = sqlite3.connect(config.DB_PATH)
    c.executescript(SCHEMA)
    return c


def normalize(addr, currency):
    """地址规范化：ETH 地址忽略大小写；其余原样"""
    a = (addr or "").strip()
    if a.lower().startswith("0x"):
        return a.lower()
    return a


def save_run(rows, source_sha, status="ok", note=""):
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:6]
    captured_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    c = _conn()
    with c:
        c.execute("INSERT INTO run VALUES (?,?,?,?,?,?)",
                  (run_id, captured_at, source_sha, len(rows), status, note))
        c.executemany("INSERT INTO snapshot VALUES (?,?,?,?,?)",
                      [(run_id, r["address"], r["currency"], r["entity"], r["fixed_ref"])
                       for r in rows])
    c.close()
    return run_id, captured_at


def last_good_run(exclude=None):
    """取上一次 status=ok 的 run_id"""
    c = _conn()
    cur = c.execute("SELECT run_id FROM run WHERE status='ok' AND run_id!=? "
                    "ORDER BY run_id DESC LIMIT 1", (exclude or "",))
    row = cur.fetchone()
    c.close()
    return row[0] if row else None


def address_set(run_id):
    """返回 set of (normalized_address, currency)"""
    c = _conn()
    cur = c.execute("SELECT address, currency FROM snapshot WHERE run_id=?", (run_id,))
    s = {(normalize(a, cur2), cur2) for a, cur2 in cur.fetchall()}
    c.close()
    return s


def diff(prev_set, curr_set):
    added   = sorted(curr_set - prev_set)
    removed = sorted(prev_set - curr_set)
    return added, removed


def lookup_details(run_id, keys):
    """把 (address, currency) 反查成含实体名的明细"""
    c = _conn()
    out = []
    for addr, cur_ in keys:
        r = c.execute("SELECT entity, fixed_ref FROM snapshot WHERE run_id=? "
                      "AND address=? AND currency=? LIMIT 1", (run_id, addr, cur_)).fetchone()
        out.append({"address": addr, "currency": cur_,
                    "entity": (r[0] if r else ""), "fixed_ref": (r[1] if r else "")})
    c.close()
    return out
