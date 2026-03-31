import sqlite3
conn = sqlite3.connect('C:/Users/Administrator/Documents/Playground/Trend_OB_AI/trades.db')
c = conn.cursor()

print('='*60)
print('2026-03-29 复盘报告')
print('='*60)

# 今日扫描
c.execute("SELECT COUNT(DISTINCT stock) FROM trades WHERE date LIKE '2026-03-29%'")
scanned = c.fetchone()[0]
print('\n【今日扫描】')
print('  股票数: %d只' % scanned)

# 有效信号
c.execute("""
    SELECT COUNT(*) FROM trades 
    WHERE date LIKE '2026-03-29%' 
    AND ((trend='UPTREND' AND ob_signal='BUY_PRESSURE') OR (trend='DOWNTREND' AND ob_signal='SELL_PRESSURE'))
""")
signals = c.fetchone()[0]
print('  有效信号: %d只' % signals)

# 趋势统计
c.execute("SELECT trend, COUNT(*) FROM trades WHERE date LIKE '2026-03-29%' GROUP BY trend")
print('\n【趋势分布】')
for r in c.fetchall():
    print('  %s: %d' % (r[0], r[1]))

# OB分布
c.execute("SELECT ob_signal, COUNT(*) FROM trades WHERE date LIKE '2026-03-29%' GROUP BY ob_signal")
print('\n【OB信号分布】')
for r in c.fetchall():
    print('  %s: %d' % (r[0], r[1]))

# 模拟交易
print('\n【模拟交易】')
c.execute('SELECT * FROM paper_positions')
positions = c.fetchall()
c.execute('SELECT cash, equity FROM paper_account')
acc = c.fetchone()
print('  持仓数: %d只' % len(positions))
print('  现金: $%.2f' % acc[0])
print('  权益: $%.2f' % acc[1])
print('  收益率: %.2f%%' % ((acc[1]-20000)/20000*100))

# 持仓明细
print('\n【持仓明细】')
total_value = 0
for p in positions:
    value = p[1] * p[2]
    total_value += value
    pct = value / acc[1] * 100
    print('  %s: %d股 @ $%.2f = $%.2f (%.1f%%)' % (p[0], p[1], p[2], value, pct))
print('  总市值: $%.2f' % total_value)
print('  仓位: %.1f%%' % (total_value/acc[1]*100))

# 订单历史
print('\n【订单历史】')
c.execute('SELECT ts, symbol, action, qty, price, reason FROM paper_orders ORDER BY ts DESC LIMIT 10')
for r in c.fetchall():
    print('  %s | %s %s %d@$%.2f | %s' % (r[0], r[2], r[1], r[3], r[4], r[5]))

conn.close()