import sqlite3
from datetime import datetime
conn = sqlite3.connect('C:/Users/Administrator/Documents/Playground/Trend_OB_AI/trades.db')
c = conn.cursor()
c.execute('SELECT COUNT(*) FROM trades')
print('Total records:', c.fetchone()[0])

c.execute("SELECT COUNT(*) FROM trades WHERE date LIKE '2026-03-31%'")
print('03-31 records:', c.fetchone()[0])

c.execute("SELECT COUNT(*) FROM trades WHERE date LIKE '2026-03-30%'")
print('03-30 records:', c.fetchone()[0])

# Recent dates
c.execute('SELECT date FROM trades ORDER BY id DESC LIMIT 3')
print('\nMost recent:')
for r in c.fetchall():
    print(r)

# Current positions with hold days
c.execute('SELECT symbol, qty, avg_cost, updated_at FROM paper_positions')
print('\nCurrent positions:')
for r in c.fetchall():
    symbol, qty, cost, updated = r
    try:
        buy_time = datetime.strptime(updated, '%Y-%m-%d %H:%M:%S')
        days = (datetime.now() - buy_time).days
        print('%s: %d @ $%.2f | %s (%dd)' % (symbol, qty, cost, updated, days))
    except:
        print('%s: %d @ $%.2f | %s' % (symbol, qty, cost, updated))

# Account
c.execute('SELECT cash, equity FROM paper_account')
acc = c.fetchone()
print('\nAccount: cash=$%.2f, equity=$%.2f' % (acc[0], acc[1]))
print('Return: %.2f%%' % ((acc[1] - 20000) / 20000 * 100))

conn.close()