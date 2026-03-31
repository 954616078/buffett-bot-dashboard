import sqlite3
conn = sqlite3.connect('C:/Users/Administrator/Documents/Playground/Trend_OB_AI/trades.db')
c = conn.cursor()
c.execute("SELECT COUNT(DISTINCT stock) FROM trades WHERE date LIKE '2026-03-17%'")
print('Unique stocks today:', c.fetchone()[0])
conn.close()
