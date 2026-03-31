import sqlite3
conn = sqlite3.connect('C:/Users/Administrator/Documents/Playground/Trend_OB_AI/trades.db')
c = conn.cursor()

# 查看COP/CSCO/CVX/PFE/HCA的记录
stocks = ['COP', 'CSCO', 'CVX', 'PFE', 'HCA']
for stock in stocks:
    c.execute("SELECT stock, date, trend, ob_signal, last_price, ai_analysis FROM trades WHERE stock=? ORDER BY id DESC LIMIT 2", (stock,))
    rows = c.fetchall()
    print(f'\n=== {stock} ===')
    for r in rows:
        print(f'{r[1]} | {r[2]} + {r[3]} | ${r[4]}')
        print(f'   {r[5][:150] if r[5] else "None"}')

conn.close()
