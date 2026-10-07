# -*- coding: utf-8 -*-
"""
SDN.CSV 加密地址统计练习 · 第一步
=====================================
背景知识：
1. SDN.CSV 官方设计就是没有表头的（列含义写在官方文档里），固定 12 列，
   列顺序 20 多年没变过——所以只要按顺序自己补一个表头就行。
2. 第 12 列 Remarks（备注）是个"大杂烩"：别名(a.k.a.)、网站、邮箱、
   加密地址全部混在这一列里。
3. 加密地址的固定格式（OFAC FAQ 563）：
       Digital Currency Address - XBT 1AbC...xyz ; alt. Digital Currency Address - ETH 0x...
   注意：同一个记录可以有多个地址、多个币种，用 "; alt." 连接。
   —— 所以不能只判断"这一行有没有"，要用正则把每个都抠出来数。

本脚本做的事：
  ① 补表头读入 CSV
  ② 筛出 Remarks 含 "Digital Currency Address" 的记录
  ③ 用正则提取每个地址的币种，按币种统计
  ④ 输出：终端统计表 + 两个结果文件（记录明细 csv / 币种统计 csv）

⚠️ 重要数据质量发现（实测）：
   平铺 SDN.CSV 的 Remarks 列在 1000 字符处会被截断！99 条含加密地址的
   记录里有 26 条被截断（如 RASHEVSKYI, Dmytro 的最后一个地址被拦腰砍断）。
   所以平铺 CSV 统计出的地址数（506）比 sdn_advanced.xml 的完整数据
   （约 977，第三方解析 2026.08 版）少了一大截。
   结论：练习用 CSV 可以；做生产级合规管道必须用 sdn_advanced.xml（结构化、
   无截断）——这正是学习材料 3.4/3.6 节强调的。
"""
import re
import pandas as pd

# ---------- ① 官方 12 列的固定顺序（照抄即可，这是 OFAC 文档定义的） ----------
SDN_COLUMNS = [
    'ent_num',        # 实体编号
    'SDN_Name',       # 被制裁主体名称
    'SDN_Type',       # 类型（individual/entity/vessel/aircraft，空为 -0-）
    'Program',        # 制裁项目（CUBA / CYBER2 / RUSSIA-EO14024 ...）
    'Title',          # 头衔（个人用）
    'Call_Sign',      # 航空器呼号
    'Vess_type',      # 船只类型
    'Tonnage',        # 吨位
    'GRT',            # 总注册吨
    'VTE',            # 车辆?
    'Other_add_info', # 其他信息
    'Remarks',        # 备注（别名/网站/邮箱/加密地址 都在这里）
]

CSV_PATH = r'C:\Users\10268\Desktop\sdn_data\sdn.csv'

# header=None  告诉 pandas 文件没有表头
# names=...    按顺序自己补上列名
# dtype=str    全部按文本读（防止 ent_num 被读成数字、地址里的科学计数法问题）
# keep_default_na=False + na_values=['']  防止 '-0-' 之类被当缺失值处理（这里简化直接 str）
df = pd.read_csv(CSV_PATH, header=None, names=SDN_COLUMNS, dtype=str,
                 keep_default_na=False)

print(f'读入 {len(df)} 行 × {df.shape[1]} 列')

# ---------- ② 筛出含加密地址的记录 ----------
# str.contains() 逐行判断 Remarks 里是否含这个短语
# na=False 的意思是：空值一律当"不包含"处理，避免报错
mask = df['Remarks'].str.contains('Digital Currency Address', na=False)
crypto = df[mask]
print(f'其中含 "Digital Currency Address" 的记录：{len(crypto)} 条')

# ---------- ③ 正则提取每个地址的币种 ----------
# 格式：Digital Currency Address - XBT 后面跟地址
# ([A-Z0-9]+) 是一个"捕获组"：匹配 1 个或多个大写字母/数字并单独取出来
pattern = r'Digital Currency Address - ([A-Z0-9]+)'

symbol_counts = {}   # {币种: 地址个数}
record_rows = []     # 每条记录的明细

for _, row in crypto.iterrows():
    # findall 返回这一行里所有匹配到的币种符号，如 ['XBT', 'XBT', 'ETH']
    symbols = re.findall(pattern, row['Remarks'])
    for s in symbols:
        symbol_counts[s] = symbol_counts.get(s, 0) + 1
    record_rows.append({
        'ent_num': row['ent_num'],
        'SDN_Name': row['SDN_Name'],
        'Program': row['Program'],
        'n_addresses': len(symbols),
        'currencies': ', '.join(sorted(set(symbols))),
    })

# ---------- ④ 输出 ----------
total_addresses = sum(symbol_counts.values())
print(f'\n提取到的加密地址总数：{total_addresses} 个')
print(f'（注意：{len(crypto)} 条记录 -> {total_addresses} 个地址，一条记录平均挂 '
      f'{total_addresses/len(crypto):.1f} 个地址）\n')

# 转成 Series 按数量降序排——这就是"按币种统计数量"
stats = pd.Series(symbol_counts, name='地址数').sort_values(ascending=False)
print('===== 按币种统计 =====')
print(stats.to_string())

# 保存结果文件（第二个练习"建最小制裁地址库"的原料）
pd.DataFrame(record_rows).to_csv(
    r'C:\Users\10268\Desktop\sdn_data\crypto_records.csv', index=False, encoding='utf-8-sig')
stats.to_csv(
    r'C:\Users\10268\Desktop\sdn_data\currency_stats.csv', encoding='utf-8-sig')
print('\n已保存: crypto_records.csv（记录明细）, currency_stats.csv（币种统计）')
