import sqlite3
conn = sqlite3.connect('C:/Users/Administrator/Documents/Playground/Trend_OB_AI/trades.db')
c = conn.cursor()

# 查看每日扫描记录
print('=== 每日扫描记录 ===\n')

c.execute("""
    SELECT date(date) as day, COUNT(DISTINCT stock) as stocks, COUNT(*) as records
    FROM trades
    GROUP BY date(date)
    ORDER BY day DESC
    LIMIT 10
""")
for r in c.fetchall():
    print(f'{r[0]}: {r[1]}只股票, {r[2]}条记录')

# 查看持仓的时间分布
print('\n=== 持仓建仓时间 ===')
c.execute("""
    SELECT symbol, avg_cost, updated_at
    FROM paper_positions
    ORDER BY updated_at
""")
for r in c.fetchall():
    print(f'{r[0]}: @${r[1]} | {r[2]}')

# 查看最近的扫描间隔
print('\n=== 最近扫描时间 ===')
c.execute("""
    SELECT date, stock, trend, ob_signal
    FROM trades
    WHERE stock='NVDA' OR stock='AAPL'
    ORDER BY date DESC
    LIMIT 10
""")
for r in c.fetchall():
    print(f'{r[0]} | {r[1]} | {r[2]} | {r[3]}')

conn.close()
