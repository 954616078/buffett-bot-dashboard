import sqlite3
conn = sqlite3.connect('C:/Users/Administrator/Documents/Playground/Trend_OB_AI/trades.db')
c = conn.cursor()

# 查看今天的信号
c.execute("""
    SELECT stock, trend, ob_signal, last_price 
    FROM trades 
    WHERE date LIKE '2026-03-17%' 
    AND ((trend='UPTREND' AND ob_signal='BUY_PRESSURE') OR (trend='DOWNTREND' AND ob_signal='SELL_PRESSURE')) 
    GROUP BY stock 
    LIMIT 10
""")
print('今日信号:')
for r in c.fetchall():
    print('%s: %s + %s @ $%.2f' % (r[0], r[1], r[2], r[3]))

# 检查是否有PAPER相关记录
c.execute("SELECT COUNT(*) FROM trades WHERE ai_analysis LIKE '%PAPER%' OR ai_analysis LIKE '%BUY%'")
print('\n交易记录:', c.fetchone()[0])

conn.close()
