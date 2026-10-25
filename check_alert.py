# -*- coding: utf-8 -*-
"""
检查第 5 步：告警规则。

怎么运行（在 PowerShell 里，先 cd 到仓库根目录）：
    python check_alert.py

应该看到 P2 / INFO / P1 三条告警。
"""
from agent import alert

rows = [
    {"address": "0x" + "1" * 40, "currency": "ETH", "entity": "TEST ENTITY", "fixed_ref": "999"},
    {"address": "not-a-valid-address", "currency": "ETH", "entity": "BAD", "fixed_ref": "998"},
]
al = alert.evaluate(
    rows,
    added=[("0x" + "1" * 40, "ETH")],
    removed=[("0x" + "2" * 40, "ETH")],
    curr_sha="x",
    prev_run_id="y",
)
for a in al:
    print(a["level"], a["code"], "|", a["message"][:60])
