# -*- coding: utf-8 -*-
"""
检查第 4 步：存档 + 差异计算。

怎么运行（在 PowerShell 里，先 cd 到仓库根目录）：
    python check_store.py

连着运行两次，第二次应该显示「新增 0 移除 0」。
"""
from agent import parse, store

rows = parse.parse_advanced_xml()
prev = store.last_good_run()
rid, ts = store.save_run(rows, source_sha="test")
print("本次 run_id：", rid, "| 上次：", prev)
if prev:
    a, r = store.diff(store.address_set(prev), store.address_set(rid))
    print("新增", len(a), "移除", len(r))
else:
    print("第一次运行，已建立基线")
