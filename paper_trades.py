import sqlite3
conn = sqlite3.connect('C:/Users/Administrator/Documents/Playground/Trend_OB_AI/trades.db')
c = conn.cursor()

# 查找模拟交易记录
c.execute("SELECT stock, ai_analysis FROM trades WHERE ai_analysis LIKE '%BUY%' OR ai_analysis LIKE '%SELL%' OR ai_analysis LIKE '%PAPER%' ORDER BY id DESC LIMIT 50")
rows = c.fetchall()

print('=== 模拟交易记录 ===')
for r in rows:
    analysis = r[1] if r[1] else 'None'
    print(f'{r[0]}: {analysis[:150]}')

# 统计
c.execute("SELECT COUNT(*) FROM trades WHERE ai_analysis LIKE '%PAPER%' OR ai_analysis LIKE '%BUY%' OR ai_analysis LIKE '%SELL%'")
total_trades = c.fetchone()[0]
print(f'\n总交易记录: {total_trades}')

conn.close()
