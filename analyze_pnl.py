import sqlite3
conn = sqlite3.connect('C:/Users/Administrator/Documents/Playground/Trend_OB_AI/trades.db')
c = conn.cursor()

# 分析每只股票的盈亏
print('=== 单只股票盈亏分析 ===\n')

c.execute("""
    SELECT 
        symbol,
        SUM(CASE WHEN action='BUY' THEN -price*qty ELSE price*qty END) as pnl
    FROM paper_orders
    GROUP BY symbol
    ORDER BY pnl
""")
rows = c.fetchall()

for r in rows:
    symbol = r[0]
    pnl = r[1]
    # 获取最新持仓
    c.execute("SELECT qty, avg_cost FROM paper_positions WHERE symbol=?", (symbol,))
    pos = c.fetchone()
    status = "持仓%d股@$%.2f" % (pos[0], pos[1]) if pos else "已平仓"
    mark = "-" if pnl < 0 else "+"
    print('%s %s: $%.2f | %s' % (mark, symbol.ljust(6), pnl, status))

# 统计止损原因
print('\n=== 止损原因分析 ===')
c.execute("""
    SELECT symbol, price, qty, realized_pnl, ts
    FROM paper_orders 
    WHERE reason='STOP_LOSS'
    ORDER BY ts DESC
""")
for r in c.fetchall():
    print('%s | %s | 卖出%d股@$%.2f | 亏损$%.2f' % (r[4], r[0], r[2], r[1], r[3]))

conn.close()
