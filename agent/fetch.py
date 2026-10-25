# -*- coding: utf-8 -*-
"""agent/fetch.py —— 拿数据，并判断有没有变化"""
import hashlib, json, os, requests
from . import config


def sha256_of(path, chunk=8 * 1024 * 1024):
    """127MB 文件不能一次读进内存，分块算哈希"""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            b = f.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def load_meta():
    if os.path.exists(config.META_PATH):
        with open(config.META_PATH, encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_meta(meta):
    with open(config.META_PATH, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)


def remote_headers():
    """只看响应头，不下载正文 —— 省 127MB 流量"""
    r = requests.head(config.SDN_URL, allow_redirects=True, timeout=60)
    r.raise_for_status()
    return {
        "last_modified": r.headers.get("Last-Modified"),
        "etag": r.headers.get("ETag"),
        "content_length": r.headers.get("Content-Length"),
    }


def download():
    """下载到 data/sdn_advanced.xml"""
    tmp = config.XML_PATH + ".tmp"
    with requests.get(config.SDN_URL, stream=True, timeout=600) as r:
        r.raise_for_status()
        with open(tmp, "wb") as f:
            for chunk in r.iter_content(8 * 1024 * 1024):
                if chunk:
                    f.write(chunk)
    os.replace(tmp, config.XML_PATH)   # 先写临时文件再替换，避免半截文件
    return sha256_of(config.XML_PATH)


def run(force=False):
    """
    返回 (changed: bool, info: dict)
    changed=True 表示需要重新解析
    """
    info = {"action": "none"}
    meta = load_meta()

    # 情况 A：本地还没有 xml —— 必须先弄一份
    if not os.path.exists(config.XML_PATH):
        print("[fetch] 本地没有 xml，开始下载……")
        info["sha256"] = download()
        info["action"] = "downloaded"
        save_meta({**meta, **info})
        return True, info

    local_sha = sha256_of(config.XML_PATH)
    info["sha256"] = local_sha

    if force:
        print("[fetch] --force：强制重新下载")
        info["sha256"] = download()
        info["action"] = "downloaded"
        save_meta({**meta, **info})
        return True, info

    # 情况 B：先看远端响应头，快速判断
    try:
        rh = remote_headers()
        info["remote"] = rh
    except Exception as e:
        print(f"[fetch] 无法连接远端（{e}），沿用本地文件")
        info["action"] = "offline_local"
        return (local_sha != meta.get("sha256")), info

    changed = (rh.get("last_modified") != meta.get("last_modified")) or \
              (rh.get("etag") != meta.get("etag"))

    if not changed:
        print("[fetch] 远端无更新，沿用本地文件")
        info["action"] = "no_change"
        save_meta({**meta, **info, "last_modified": rh.get("last_modified"),
                   "etag": rh.get("etag")})
        return (local_sha != meta.get("sha256")), info

    print("[fetch] 检测到远端更新，重新下载……")
    info["sha256"] = download()
    info["action"] = "downloaded"
    save_meta({**meta, **info, "last_modified": rh.get("last_modified"),
               "etag": rh.get("etag")})
    return True, info
