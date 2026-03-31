import sqlite3
conn = sqlite3.connect('C:/Users/Administrator/Documents/Playground/Trend_OB_AI/trades.db')
c = conn.cursor()

c.execute("SELECT COUNT(*) FROM trades WHERE date LIKE '2026-03-29%'")
print('今日记录:', c.fetchone()[0])

c.execute('SELECT MAX(id) FROM trades')
print('Max ID:', c.fetchone()[0])

c.execute("SELECT COUNT(*) FROM trades WHERE date LIKE '2026-03-28%'")
print('昨日记录:', c.fetchone()[0])

conn.close()