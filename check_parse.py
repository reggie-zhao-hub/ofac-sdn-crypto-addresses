# -*- coding: utf-8 -*-
"""
检查第 3 步：解析器。

怎么运行（在 PowerShell 里，先 cd 到仓库根目录）：
    python check_parse.py

地址总数应该是 1059 左右，和你 step2 跑出来的一致。
注意：需要 data/sdn_advanced.xml 已经就位（或用环境变量 OFAC_SDN_XML 指向它）。
"""
from agent import parse

rows = parse.parse_advanced_xml()
print("地址总数：", len(rows))
print("前 3 条：", rows[:3])
