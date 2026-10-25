# -*- coding: utf-8 -*-
"""
检查第 2 步：下载 + 变更检测。

怎么运行（在 PowerShell 里，先 cd 到仓库根目录）：
    python check_fetch.py

第一次运行，changed 应该是 True（因为还没有历史记录可对比）。
"""
from agent import fetch

changed, info = fetch.run()
print("changed =", changed)
print(info)
