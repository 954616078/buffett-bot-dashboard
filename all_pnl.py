import sqlite3
conn = sqlite3.connect('C:/Users/Administrator/Documents/Playground/Trend_OB_AI/trades.db')
c = conn.cursor()

# 查找所有pnl记录
c.execute("SELECT stock, date, ai_analysis FROM trades WHERE ai_analysis LIKE '%pnl=%' OR ai_analysis LIKE '%STOP_LOSS%' ORDER BY id DESC LIMIT 20")
rows = c.fetchall()

print('=== 所有交易盈亏记录 ===')
for r in rows:
    print(f'{r[0]} | {r[1]}')
    print(f'   {r[2][:200]}')

# 统计
c.execute("SELECT COUNT(*) FROM trades WHERE ai_analysis LIKE '%pnl=%'")
total = c.fetchone()[0]
print(f'\n总交易次数: {total}')

conn.close()
