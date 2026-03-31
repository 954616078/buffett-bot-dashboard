import sqlite3
conn = sqlite3.connect('C:/Users/Administrator/Documents/Playground/Trend_OB_AI/trades.db')
c = conn.cursor()

# 统计今天有效信号
c.execute("SELECT COUNT(*) FROM trades WHERE date LIKE '2026-03-17%'")
total = c.fetchone()[0]
c.execute("SELECT COUNT(DISTINCT stock) FROM trades WHERE date LIKE '2026-03-17%'")
unique = c.fetchone()[0]

print('今日扫描: %d只股票, %d条记录' % (unique, total))

# 检查最新订单
c.execute('SELECT id, ts, symbol, action, qty, price, reason, realized_pnl FROM paper_orders ORDER BY id DESC')
print('\n订单:')
for r in c.fetchall():
    print('%d | %s | %s | %s | %d @ $%.2f | %s | pnl=%.2f' % (r[0], r[1], r[2], r[3], r[4], r[5], r[6], r[7]))

c.execute('SELECT symbol, qty, avg_cost FROM paper_positions')
print('\n持仓:')
for r in c.fetchall():
    print('%s: %d @ $%.2f' % (r[0], r[1], r[2]))

c.execute('SELECT cash, equity FROM paper_account')
acc = c.fetchone()
print('\n账户: cash=%.2f, equity=%.2f' % (acc[0], acc[1]))

# 计算新参数下的仓位
print('\n=== 新参数效果 ===')
print('仓位限制: 5%单票, 0.5%单笔风险')
print('CVX仓位: $984.2 / $20000 = 4.9% (符合5%限制)')

conn.close()
