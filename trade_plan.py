import sqlite3
conn = sqlite3.connect('C:/Users/Administrator/Documents/Playground/Trend_OB_AI/trades.db')
c = conn.cursor()

# 最近记录
c.execute('SELECT stock, trend, ob_signal, last_price, date FROM trades ORDER BY id DESC LIMIT 50')
rows = c.fetchall()

# 统计
c.execute("SELECT COUNT(*) FROM trades WHERE date LIKE '2026-03-17%'")
today_count = c.fetchone()[0]

print('=== 今日交易计划 ===')
print(f'今日扫描: {today_count}条')
print()

# 按股票分组，取最新
stocks = {}
for r in rows:
    s = r[0]
    if s not in stocks:
        stocks[s] = r

# 筛选有效信号 (UPTREND+BUY_PRESSURE 或 DOWNTREND+SELL_PRESSURE)
signals = []
for s, r in stocks.items():
    trend = r[1]
    ob = r[2]
    if (trend == 'UPTREND' and ob == 'BUY_PRESSURE') or (trend == 'DOWNTREND' and ob == 'SELL_PRESSURE'):
        signals.append(r)

print(f'有效信号 ({len(signals)}只):')
if signals:
    for s in signals:
        print(f'  {s[0]} | {s[1]} | {s[2]} | \${s[3]}')
else:
    print('  无')

# 有趋势但无OB的
no_ob = []
for s, r in stocks.items():
    if r[1] in ('UPTREND', 'DOWNTREND') and r[2] == 'NO_OB_DATA':
        no_ob.append(r)

print()
print(f'有趋势但无OB数据 ({len(no_ob)}只):')
for r in no_ob[:10]:
    print(f'  {r[0]} | {r[1]} | \${r[3]}')

conn.close()
