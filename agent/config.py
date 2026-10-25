# -*- coding: utf-8 -*-
"""agent/config.py —— 所有路径和常量集中在这里"""
import os

# 仓库根目录 = agent/ 的上一级
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DATA_DIR     = os.path.join(ROOT, "data")
SNAPSHOT_DIR = os.path.join(ROOT, "snapshots")
ALERT_DIR    = os.path.join(ROOT, "alerts")

# xml 路径：默认 data/sdn_advanced.xml，可用环境变量覆盖
XML_PATH = os.environ.get("OFAC_SDN_XML") or os.path.join(DATA_DIR, "sdn_advanced.xml")
DB_PATH  = os.path.join(DATA_DIR, "sdn_agent.db")
META_PATH= os.path.join(DATA_DIR, "source_meta.json")

# OFAC 官方导出端点（若 404，去官网 Sanctions List Service 页面取当前链接后替换）
SDN_URL = ("https://sanctionslistservice.ofac.treas.gov/api/PublicationPreview"
           "/exports/ADVANCED_XML")

# 和 step2 保持一致的命名空间，别改
NS = "{https://sanctionslistservice.ofac.treas.gov/api/PublicationPreview/exports/ADVANCED_XML}"

for _d in (DATA_DIR, SNAPSHOT_DIR, ALERT_DIR):
    os.makedirs(_d, exist_ok=True)
