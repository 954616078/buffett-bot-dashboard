import sqlite3
conn = sqlite3.connect('C:/Users/Administrator/Documents/Playground/Trend_OB_AI/trades.db')
c = conn.cursor()

# 查看今日有效信号
c.execute("""
    SELECT stock, trend, ob_signal, last_price 
    FROM trades 
    WHERE date LIKE '2026-03-17%' 
    AND ((trend='UPTREND' AND ob_signal='BUY_PRESSURE') OR (trend='DOWNTREND' AND ob_signal='SELL_PRESSURE')) 
    GROUP BY stock 
    ORDER BY stock
""")
signals = c.fetchall()

print('今日有效信号: %d只' % len(signals))
for s in signals:
    print('%s: %s + %s @ $%.2f' % (s[0], s[1], s[2], s[3]))

# 查看持仓
c.execute('SELECT COUNT(*) FROM paper_positions')
pos_count = c.fetchone()[0]
print('\n当前持仓数: %d' % pos_count)

# 查看账户
c.execute('SELECT cash, equity FROM paper_account')
acc = c.fetchone()
print('账户: cash=%.2f, equity=%.2f' % (acc[0], acc[1]))

conn.close()
