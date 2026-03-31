import sqlite3
conn = sqlite3.connect('C:/Users/Administrator/Documents/Playground/Trend_OB_AI/trades.db')
c = conn.cursor()
c.execute("SELECT stock, trend, ob_signal, ai_analysis FROM trades ORDER BY id DESC LIMIT 20")
rows = c.fetchall()
print("最近20条记录:")
for r in rows:
    print(f"{r[0]} | {r[1]} | {r[2]} | {r[3][:50] if r[3] else 'None'}...")
conn.close()
