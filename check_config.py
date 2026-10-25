# -*- coding: utf-8 -*-
"""
检查第 1 步：config.py 有没有写对。

怎么运行（在 PowerShell 里，先 cd 到仓库根目录）：
    python check_config.py

看到下面两个路径打印出来、没有红色报错，就是对的。
"""
from agent import config

print("仓库根目录（ROOT）：", config.ROOT)
print("xml 文件路径（XML_PATH）：", config.XML_PATH)
