# -*- coding: utf-8 -*-
"""
SDN 加密地址解析 · 第二步：sdn_advanced.xml（生产级数据源）
============================================================
为什么用 advanced XML 而不是平铺 CSV：
  平铺 CSV 的 Remarks 在 1000 字符截断（第一步实测 99 条记录丢了 26 条尾部），
  advanced XML 是结构化的——每个地址独立一个 Feature 节点，无截断、带币种、
  可靠性标记齐全。真实合规管道对接的就是它。

XML 的设计（对着读，一遍就懂）：
  <Sanctions>                        <- 根节点
    <ReferenceValueSets>             <- 查找表区（在文件前部）
      <FeatureTypeValues>
        <FeatureType ID="345">Digital Currency Address - ETH</FeatureType>
        ...每个币种一个 ID（344=XBT, 345=ETH, 992=TRX ...）
      </FeatureTypeValues>
    </ReferenceValueSets>
    <DistinctParty FixedRef="4632">  <- 每个被制裁主体一条
      <Profile>
        <Identity Primary="true">
          <Alias Primary="true">     <- 主名称在这
            <DocumentedName>...<NamePartValue>央行英文名</NamePartValue>
        </Identity>
        <Feature FeatureTypeID="345"> <- 币种靠 ID 引用上面的查找表！
          <FeatureVersion>
            <VersionDetail>0x098B...</VersionDetail>  <- 地址本体
      ...

关键工程点（都是面试考点）：
  ① 127MB 不能整棵树读进内存 -> 用 iterparse 流式解析（SAX 思想的简写版）
  ② 读完每个 DistinctParty 要 elem.clear()，否则内存照样被撑爆
  ③ 文件用数字 ID 引用查找表 -> 必须先扫完 ReferenceValueSets 再处理主体
     （幸好 OFAC 把查找表放在文件前部，顺序读一遍正好）

输出：终端统计 + sdn_addresses.csv（最小"制裁地址库"，第二步练习的产出）

⚠️ 实测数据质量发现（第三步的伏笔）——1059 行里有 16 组重复地址，分三类：
  ① 同一地址、同一主体、不同币种标签（SUEX 的地址同时标 ETH+USDT+XBT：
     同一个 EVM 地址可以持有多种代币）。含义：筛查时"地址"才是主键，
     币种只是元数据——用 (地址, 币种) 当主键会漏报。
  ② 同一地址挂在不同主体名下（Khatibi 和 Nikaeen Ravari 共用一个 XBT 地址、
     RAZA 和 Secondeye 共用一个 LTC 地址）。含义：共享地址正是调查人员
     关联两个实体的"链上握手"证据——地址复用是最古老的链上线索。
  ③ 纯重复（Blender.io 同一地址列了两次，可能来自两个制裁项目条目）。
"""
import time
import re
import xml.etree.ElementTree as ET
import pandas as pd

XML_PATH = r'C:\Users\10268\Desktop\sdn_data\sdn_advanced.xml'
NS = '{https://sanctionslistservice.ofac.treas.gov/api/PublicationPreview/exports/ADVANCED_XML}'

t0 = time.time()

# ---------- ① 先扫描查找表：币种 ID -> 币种符号 ----------
# "Digital Currency Address - ETH" 取最后的 ETH
symbol_of = {}          # {FeatureType ID: 'ETH'}
for _, elem in ET.iterparse(XML_PATH, events=('end',)):
    if elem.tag == NS + 'FeatureType' and (elem.text or '').startswith('Digital Currency Address'):
        m = re.search(r'- ([A-Z0-9]+)$', elem.text)
        if m:
            symbol_of[elem.get('ID')] = m.group(1)
    if elem.tag == NS + 'FeatureTypeValues':
        break   # 查找表扫完了，后面全是主体记录
print(f'查找表：{len(symbol_of)} 个币种 ID（{time.time()-t0:.1f}s）')

# ---------- ② 流式处理每个被制裁主体 ----------
# events 里加 'start' 是为了拿到根节点引用——读完后 clear 它，防止整棵树留在内存
root = None
n_parties = 0          # 主体总数
n_crypto_parties = 0   # 含加密地址的主体数
rows = []              # 明细行

for event, elem in ET.iterparse(XML_PATH, events=('start', 'end')):
    if event == 'start':
        if root is None:
            root = elem
        continue
    if elem.tag != NS + 'DistinctParty':
        continue

    n_parties += 1

    # 主名称：找 Primary="true" 的 Alias 下的 NamePartValue，按顺序拼接
    name = ''
    for alias in elem.iter(NS + 'Alias'):
        if alias.get('Primary') == 'true':
            parts = [v.text or '' for v in alias.iter(NS + 'NamePartValue')]
            name = ' '.join(p for p in parts if p)
            break

    # 加密地址：FeatureTypeID 命中查找表的，把 VersionDetail 的文本抠出来
    for feature in elem.iter(NS + 'Feature'):
        sym = symbol_of.get(feature.get('FeatureTypeID'))
        if sym is None:
            continue
        detail = feature.find(f'{NS}FeatureVersion/{NS}VersionDetail')
        if detail is not None and detail.text:
            rows.append({
                'address': detail.text.strip(),
                'currency': sym,
                'entity': name,
                'fixed_ref': elem.get('FixedRef'),
            })

    elem.clear()     # 释放这个主体，内存保持平坦
    root.clear()     # 把处理完的兄弟节点也从树上摘掉

# 含加密地址的主体数：对 fixed_ref 去重计数（一个主体挂多个地址）
n_crypto_parties = len(set(r['fixed_ref'] for r in rows))

# ---------- ③ 统计输出 ----------
df = pd.DataFrame(rows)
print(f'扫描完成：{n_parties} 个主体，其中 {n_crypto_parties} 个挂加密地址，'
      f'共 {len(df)} 个地址（{time.time()-t0:.1f}s）\n')

print('===== 按币种统计（advanced XML 完整数据）=====')
stats = df['currency'].value_counts()
print(stats.to_string())

# ---------- ④ 与第一步 CSV 结果对比 ----------
csv_stats = pd.read_csv(r'C:\Users\10268\Desktop\sdn_data\currency_stats.csv',
                        index_col=0).iloc[:, 0]
cmp = pd.DataFrame({'CSV(截断)': csv_stats, 'XML(完整)': stats}).fillna(0).astype(int)
cmp['丢失'] = cmp['XML(完整)'] - cmp['CSV(截断)']
print('\n===== CSV vs XML 对比（截断丢了多少）=====')
print(cmp.sort_values('丢失', ascending=False).to_string())

# ---------- ⑤ 保存最小"制裁地址库" ----------
df.to_csv(r'C:\Users\10268\Desktop\sdn_data\sdn_addresses.csv',
          index=False, encoding='utf-8-sig')
print(f'\n已保存: sdn_addresses.csv（{len(df)} 行 × {len(df.columns)} 列）——最小制裁地址库')
print('这就是合规管道的输入表：日常业务只需拿地址来精确匹配这张表，')
print('再配合地址聚类/直接/间接关联做扩展（第三步的学习内容）。')
