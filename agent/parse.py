# -*- coding: utf-8 -*-
"""agent/parse.py —— 解析 advanced XML（逻辑来自 step2_advanced_xml.py）"""
import re, time
import xml.etree.ElementTree as ET
from . import config

NS = config.NS


def _scan_symbol_table(xml_path):
    """第一遍：只扫查找表，拿到 币种ID -> 币种符号"""
    symbol_of = {}
    for _, elem in ET.iterparse(xml_path, events=("end",)):
        if elem.tag == NS + "FeatureType" and (elem.text or "").startswith("Digital Currency Address"):
            m = re.search(r"- ([A-Z0-9]+)$", elem.text)
            if m:
                symbol_of[elem.get("ID")] = m.group(1)
        if elem.tag == NS + "FeatureTypeValues":
            break          # 查找表扫完，后面全是主体，停
    return symbol_of


def parse_advanced_xml(xml_path=None):
    """
    返回 rows: list of dict(address, currency, entity, fixed_ref)
    流式解析，内存保持平坦（127MB 也不会爆）
    """
    xml_path = xml_path or config.XML_PATH
    t0 = time.time()

    symbol_of = _scan_symbol_table(xml_path)
    print(f"[parse] 查找表：{len(symbol_of)} 个币种 ID（{time.time()-t0:.1f}s）")

    rows, root, n_parties = [], None, 0
    for event, elem in ET.iterparse(xml_path, events=("start", "end")):
        if event == "start":
            if root is None:
                root = elem
            continue
        if elem.tag != NS + "DistinctParty":
            continue

        n_parties += 1
        if n_parties % 2000 == 0:
            print(f"[parse] 已扫 {n_parties} 个主体……")

        name = ""
        for alias in elem.iter(NS + "Alias"):
            if alias.get("Primary") == "true":
                parts = [v.text or "" for v in alias.iter(NS + "NamePartValue")]
                name = " ".join(x for x in parts if x)
                break

        for feature in elem.iter(NS + "Feature"):
            sym = symbol_of.get(feature.get("FeatureTypeID"))
            if sym is None:
                continue
            detail = feature.find(f"{NS}FeatureVersion/{NS}VersionDetail")
            if detail is not None and detail.text:
                rows.append({
                    "address":   detail.text.strip(),
                    "currency":  sym,
                    "entity":    name,
                    "fixed_ref": elem.get("FixedRef"),
                })

        elem.clear()
        root.clear()      # 关键：不让整棵树留在内存

    print(f"[parse] 完成：{n_parties} 个主体，{len(rows)} 个地址（{time.time()-t0:.1f}s）")
    return rows
