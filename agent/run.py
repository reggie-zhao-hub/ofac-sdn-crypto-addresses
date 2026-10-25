# -*- coding: utf-8 -*-
"""agent/run.py —— 主入口：fetch -> parse -> validate -> store -> diff -> alert"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent import config, fetch, parse, store, alert


def main(force=False):
    changed, info = fetch.run(force=force)

    # 远端没变、本地也没变，且已有基线 —— 直接结束
    prev_run = store.last_good_run()
    if not changed and prev_run:
        print("[run] 无变化，本次不重新解析。")
        return 0

    rows = parse.parse_advanced_xml()

    prev_set = store.address_set(prev_run) if prev_run else set()
    added, removed = store.diff(prev_set, {
        (store.normalize(r["address"], r["currency"]), r["currency"]) for r in rows
    })

    # P0 判定：解析为空时不写入基线，直接告警退出
    status = "ok" if rows else "empty"
    run_id, captured_at = store.save_run(rows, info.get("sha256", ""), status=status)

    alerts = alert.evaluate(rows, added, removed, info.get("sha256", ""), prev_run)
    added_details   = store.lookup_details(run_id, added) if added else []
    removed_details = store.lookup_details(prev_run, removed) if (removed and prev_run) else []

    path = alert.write_report(alerts, run_id, captured_at, added_details, removed_details)

    print(f"\n[run] 完成 run_id={run_id}")
    print(f"[run] 地址 {len(rows)} 个 | 新增 {len(added)} | 移除 {len(removed)}")
    for a in alerts:
        print(f"[run] {a['level']:4s} {a['code']}: {a['message']}")
    print(f"[run] 告警文件：{path}")

    return 1 if any(a["level"] == "P0" for a in alerts) else 0


if __name__ == "__main__":
    sys.exit(main(force="--force" in sys.argv))
