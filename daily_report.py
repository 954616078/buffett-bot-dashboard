import sqlite3
conn = sqlite3.connect('C:/Users/Administrator/Documents/Playground/Trend_OB_AI/trades.db')
c = conn.cursor()

# 今日记录
c.execute("SELECT COUNT(*) FROM trades WHERE date LIKE '2026-03-11%'")
total = c.fetchone()[0]

# 趋势统计
c.execute("SELECT trend, COUNT(*) FROM trades WHERE date LIKE '2026-03-11%' GROUP BY trend")
trend_stats = c.fetchall()

# OB统计
c.execute("SELECT ob_signal, COUNT(*) FROM trades WHERE date LIKE '2026-03-11%' GROUP BY ob_signal")
ob_stats = c.fetchall()

# 有趋势的股票
c.execute("SELECT stock, trend, ob_signal, last_price FROM trades WHERE date LIKE '2026-03-11%' AND (trend='UPTREND' OR trend='DOWNTREND') GROUP BY stock ORDER BY stock")
stocks = c.fetchall()

print('=== 今日前100监控简报 ===')
print(f'总扫描: {total}')
print()
print('趋势分布:')
for t, n in trend_stats:
    print(f'  {t}: {n}')
print()
print('OB信号分布:')
for o, n in ob_stats:
    print(f'  {o}: {n}')
print()
print('有趋势的股票 (共{}只):'.format(len(stocks)))
for s in stocks:
    print(f'  {s[0]} | {s[1]} | {s[2]} | ${s[3]}')
conn.close()
