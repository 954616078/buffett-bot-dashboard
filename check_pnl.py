import sqlite3
conn = sqlite3.connect('C:/Users/Administrator/Documents/Playground/Trend_OB_AI/trades.db')
c = conn.cursor()

# 查找PFE和HCA的止损记录
c.execute("SELECT stock, date, ai_analysis FROM trades WHERE ai_analysis LIKE '%STOP_LOSS%' ORDER BY id DESC")
rows = c.fetchall()

print('=== 止损记录 ===')
for r in rows:
    print(f'{r[0]} | {r[1]}')
    print(f'   {r[2]}')

# 查看最新持仓
c.execute("SELECT stock, last_price, date FROM trades WHERE stock IN ('COP', 'CSCO', 'CVX') ORDER BY id DESC LIMIT 3")
print('\n=== 当前持仓 ===')
for r in c.fetchall():
    print(f'{r[0]}: ${r[1]} (扫描时间: {r[2]})')

conn.close()
