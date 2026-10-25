# -*- coding: utf-8 -*-
"""agent/alert.py —— 判断规则与告警输出"""
import os, re
from datetime import datetime
from . import config

# 每种币种的合法地址格式（只校验主流，其他放行）
PATTERNS = {
    "ETH": re.compile(r"^0x[0-9a-fA-F]{40}$"),
    # XBT: legacy(1/3) 与 bech32(bc1) 两类
    "XBT": re.compile(r"^(1|3)[a-zA-Z0-9]{25,34}$|^bc1[a-zA-Z0-9]{39,59}$"),
    # LTC: legacy(L/M/3) 与 bech32(ltc1) 两类——ltc1 是 2020 年后常见格式，别漏
    "LTC": re.compile(r"^[LM3][a-zA-Z0-9]{26,33}$|^ltc1[a-zA-Z0-9]{39,43}$"),
    "TRX": re.compile(r"^T[a-zA-Z0-9]{33}$"),
    "XMR": re.compile(r"^[48][a-zA-Z0-9]{94,105}$"),
}

# 已知需要人工研判、但不阻断的特例（实测发现，见 README）
KNOWN_ANOMALIES = {
    "5be5543ff73456ab9f2d207887e2af87322c651ea1a873c5b25b7ffae456c320":
        "XMR 地址长度 64（非标准 95），疑为 payment id 或 OFAC 录入问题，需人工确认",
    "TUCsTq7TofTCJRRoHk6RvhMoS2mJLm5Yzq":
        "标记为 XBT 但以 T 开头、长度 34，格式上更像 TRX 地址，疑为 OFAC 币种标签错误，需人工确认",
}


def validate_address(addr, currency):
    pat = PATTERNS.get(currency)
    if pat is None:
        return bool(addr and addr.strip())
    return bool(pat.match(addr or ""))


def evaluate(rows, added, removed, curr_sha, prev_run_id):
    """返回告警列表，每条含 level / code / message"""
    alerts = []

    # P0：解析出 0 个地址 —— 最危险的情况
    if len(rows) == 0:
        alerts.append({
            "level": "P0", "code": "EMPTY_PARSE",
            "message": "本次解析出 0 个地址。可能是下载损坏或源格式变更。"
                       "不得当作「无制裁地址」使用，请立即人工核查。",
        })

    # P2：格式校验（已登记为已知异常的不重复计入，但会在报告里单列）
    bad = [(r["address"], r["currency"]) for r in rows
           if not validate_address(r["address"], r["currency"])
           and r["address"] not in KNOWN_ANOMALIES]
    if bad:
        alerts.append({
            "level": "P2", "code": "FORMAT_INVALID",
            "message": f"{len(bad)} 个地址格式校验未通过，例：{bad[:3]}。"
                       f"可能是 OFAC 录入问题或出现新格式。",
        })
    known_hit = [r for r in rows if r["address"] in KNOWN_ANOMALIES]
    if known_hit:
        alerts.append({
            "level": "P2", "code": "KNOWN_ANOMALY",
            "message": f"命中 {len(known_hit)} 条已登记的历史异常（详见 README 的 Known anomalies 一节），"
                       f"本次不做重复告警处置，但需保持跟踪。",
        })

    # P1：新增过多
    if len(added) > 100:
        alerts.append({
            "level": "P1", "code": "BULK_ADD",
            "message": f"单次新增 {len(added)} 个地址（阈值 100）。"
                       f"需人工确认是 OFAC 批量更新，还是解析口径变化导致的假阳性。",
        })
    elif added:
        alerts.append({
            "level": "INFO", "code": "ROUTINE_ADD",
            "message": f"新增 {len(added)} 个地址，属日常更新。",
        })

    # P1：移除（只报不删）
    if removed:
        alerts.append({
            "level": "P1", "code": "POSSIBLE_DELIST",
            "message": f"有 {len(removed)} 个地址不再出现在名单中。"
                       f"可能意味着解禁或条目修正——程序不会自动删除，需人工审批后处置。",
        })

    if not alerts:
        alerts.append({"level": "INFO", "code": "NO_CHANGE", "message": "本次无变化。"})

    return alerts


def write_report(alerts, run_id, captured_at, added_details, removed_details):
    """写成人类可读的 markdown，放进 alerts/ 目录"""
    day = datetime.now().strftime("%Y-%m-%d")
    path = os.path.join(config.ALERT_DIR, f"{day}.md")
    lines = [
        f"# SDN 监控告警 · {day}",
        "",
        f"- run_id：`{run_id}`",
        f"- 采集时间（UTC）：{captured_at}",
        f"- 对比基线：{'(首次)' }",
        "",
        "## 告警",
        "",
        "| 级别 | 代码 | 说明 |",
        "|---|---|---|",
    ]
    for a in alerts:
        lines.append(f"| {a['level']} | {a['code']} | {a['message']} |")

    if added_details:
        lines += ["", "## 新增地址（明细）", "", "| 币种 | 地址 | 实体 |", "|---|---|---|"]
        for d in added_details[:50]:
            lines.append(f"| {d['currency']} | `{d['address']}` | {d['entity']} |")
        if len(added_details) > 50:
            lines.append(f"| … | 另有 {len(added_details)-50} 条 | |")

    if removed_details:
        lines += ["", "## 疑似移除（需人工确认，程序未自动删除）", "",
                  "| 币种 | 地址 | 实体 |", "|---|---|---|"]
        for d in removed_details[:50]:
            lines.append(f"| {d['currency']} | `{d['address']}` | {d['entity']} |")

    lines += ["", "---", "本文件由 ofac-sdn-crypto-addresses agent 自动生成。",
              "告警不等于处置：所有 P1 及以上条目均需人工确认。"]

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    return path
