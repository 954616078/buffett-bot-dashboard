import sqlite3
conn = sqlite3.connect('C:/Users/Administrator/Documents/Playground/Trend_OB_AI/trades.db')
c = conn.cursor()

# 今日统计
c.execute("SELECT COUNT(*) FROM trades WHERE date LIKE '2026-03-17%'")
total = c.fetchone()[0]

c.execute("SELECT COUNT(DISTINCT stock) FROM trades WHERE date LIKE '2026-03-17%'")
unique = c.fetchone()[0]

# 趋势统计
c.execute("SELECT trend, COUNT(*) FROM trades WHERE date LIKE '2026-03-17%' GROUP BY trend")
trend_stats = c.fetchall()

# OB统计
c.execute("SELECT ob_signal, COUNT(*) FROM trades WHERE date LIKE '2026-03-17%' GROUP BY ob_signal")
ob_stats = c.fetchall()

print('='*50)
print('2026-03-17 交易计划')
print('='*50)
print(f'扫描: {unique}只股票, {total}条记录')
print()

print('【趋势分布】')
for t, n in trend_stats:
    print(f'  {t}: {n}')
print()

print('【OB信号分布】')
for o, n in ob_stats:
    print(f'  {o}: {n}')
print()

# 对齐信号
c.execute("""
    SELECT stock, trend, ob_signal, last_price 
    FROM trades 
    WHERE date LIKE '2026-03-17%' 
    AND ((trend='UPTREND' AND ob_signal='BUY_PRESSURE') OR (trend='DOWNTREND' AND ob_signal='SELL_PRESSURE'))
    GROUP BY stock
    ORDER BY stock
""")
signals = c.fetchall()

print(f'【有效信号】({len(signals)}只)')
for s in signals:
    action = '买入' if s[1] == 'UPTREND' else '卖出'
    print(f'  {action} {s[0]} | {s[1]} + {s[2]} | \${s[3]}')

conn.close()
