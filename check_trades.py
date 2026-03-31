import sqlite3
conn = sqlite3.connect('C:/Users/Administrator/Documents/Playground/Trend_OB_AI/trades.db')
c = conn.cursor()

# 查看PAPER交易详情
c.execute("SELECT stock, ai_analysis FROM trades WHERE ai_analysis LIKE '%BUY%' OR ai_analysis LIKE '%SELL%' ORDER BY id DESC LIMIT 10")
print('最近交易:')
for r in c.fetchall():
    print(r[0], '|', r[1][:80])

conn.close()
