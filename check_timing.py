import sqlite3
conn = sqlite3.connect('C:/Users/Administrator/Documents/Playground/Trend_OB_AI/trades.db')
c = conn.cursor()

# 检查交易记录的时间
c.execute("SELECT stock, date, ai_analysis FROM trades WHERE ai_analysis LIKE '%建仓%' OR ai_analysis LIKE '%BUY%' ORDER BY date DESC LIMIT 10")
print('交易记录时间:')
for r in c.fetchall():
    print(r[1], '|', r[0][:6], '|', r[2][:50])

# 检查paper_orders时间
print('\nPaper orders:')
c.execute("SELECT * FROM paper_orders")
for r in c.fetchall():
    print(r)

conn.close()
