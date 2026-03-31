import sqlite3
from datetime import datetime

conn = sqlite3.connect('C:/Users/Administrator/Documents/Playground/Trend_OB_AI/trades.db')
c = conn.cursor()

# 重置账户
c.execute("DELETE FROM paper_orders")
c.execute("DELETE FROM paper_positions")
c.execute("DELETE FROM paper_account")

now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
c.execute("INSERT INTO paper_account (id, cash, equity, risk_pct, updated_at) VALUES (1, 20000, 20000, 0.005, ?)", (now,))

conn.commit()
print('模拟账户已重置')

# 确认
c.execute('SELECT * FROM paper_account')
print(c.fetchall())

# 确认持仓已清空
c.execute('SELECT COUNT(*) FROM paper_positions')
print('持仓数量:', c.fetchone()[0])

conn.close()
