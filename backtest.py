import sqlite3
from datetime import datetime, timedelta

conn = sqlite3.connect('C:/Users/Administrator/Documents/Playground/Trend_OB_AI/trades.db')
c = conn.cursor()

print('='*60)
print('回测分析: 新参数 vs 旧参数')
print('='*60)

# 获取所有历史交易
c.execute("""
    SELECT ts, symbol, action, qty, price, reason, realized_pnl
    FROM paper_orders
    ORDER BY ts
""")
orders = c.fetchall()

print('\n【历史交易记录】')
total_pnl = 0
win = 0
loss = 0
for o in orders:
    ts, symbol, action, qty, price, reason, pnl = o
    total_pnl += pnl
    if pnl > 0:
        win += 1
    elif pnl < 0:
        loss += 1
    mark = '+' if pnl >= 0 else ''
    print('%s | %s %s %d@$%.2f | %s | %s%.2f' % (ts, action, symbol, qty, price, reason, mark, pnl))

print('\n【盈亏统计】')
print('总交易: %d次' % len(orders))
print('盈利: %d次' % win)
print('亏损: %d次' % loss)
print('胜率: %.1f%%' % (win/(win+loss)*100 if win+loss > 0 else 0))
print('总盈亏: $%.2f' % total_pnl)

# 按日期统计
print('\n【每日盈亏】')
c.execute("""
    SELECT date(ts) as day, SUM(realized_pnl) as pnl, COUNT(*) as cnt
    FROM paper_orders
    GROUP BY date(ts)
    ORDER BY day
""")
for r in c.fetchall():
    print('%s: %d笔, pnl=$%.2f' % (r[0], r[2], r[1]))

# 持仓分析
print('\n【当前持仓】')
c.execute('SELECT symbol, qty, avg_cost FROM paper_positions')
for r in c.fetchall():
    print('%s: %d股 @ $%.2f' % (r[0], r[1], r[2]))

# 优化建议
print('\n【优化建议】')
print('1. 已调整仓位: 5%单票 (原15%)')
print('2. 已调整止损: 1.5% (原2%)')
print('3. 已调整止盈: 6% (原4%)')
print('4. 新增最大持仓: 5只')

conn.close()
