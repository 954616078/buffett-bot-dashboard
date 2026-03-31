import sqlite3
conn = sqlite3.connect('C:/Users/Administrator/Documents/Playground/Trend_OB_AI/trades.db')
c = conn.cursor()

# 统计所有盈亏
c.execute('SELECT SUM(realized_pnl) FROM paper_orders')
total_pnl = c.fetchone()[0]

# 统计止损次数
c.execute("SELECT COUNT(*) FROM paper_orders WHERE reason='STOP_LOSS'")
stop_loss_count = c.fetchone()[0]

# 统计止盈次数
c.execute("SELECT COUNT(*) FROM paper_orders WHERE reason='TAKE_PROFIT'")
tp_count = c.fetchone()[0]

# 总交易次数
c.execute('SELECT COUNT(*) FROM paper_orders')
total_trades = c.fetchone()[0]

# 账户初始资金
initial = 20000

# 当前账户
c.execute('SELECT cash, equity FROM paper_account')
acc = c.fetchone()

print('='*50)
print('模拟交易盈亏汇总')
print('='*50)
print(f'初始资金: ${initial}')
print(f'当前现金: ${acc[0]:.2f}')
print(f'当前权益: ${acc[1]:.2f}')
print(f'总盈亏: ${total_pnl:.2f}')
print(f'收益率: {(acc[1]-initial)/initial*100:.2f}%')
print()
print(f'总交易次数: {total_trades}')
print(f'止损次数: {stop_loss_count}')
print(f'止盈次数: {tp_count}')
print(f'胜率: {(total_trades-stop_loss_count)/total_trades*100:.1f}%')

conn.close()
