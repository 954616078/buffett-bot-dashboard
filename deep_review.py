import sqlite3
from collections import defaultdict

conn = sqlite3.connect('C:/Users/Administrator/Documents/Playground/Trend_OB_AI/trades.db')
c = conn.cursor()

# 今日信号统计
c.execute("""
    SELECT stock, trend, ob_signal, last_price, ai_analysis
    FROM trades 
    WHERE date LIKE '2026-03-17%'
    AND ((trend='UPTREND' AND ob_signal='BUY_PRESSURE') OR (trend='DOWNTREND' AND ob_signal='SELL_PRESSURE'))
    GROUP BY stock
    ORDER BY trend, stock
""")
signals = c.fetchall()

# 统计
buy_signals = [s for s in signals if s[1] == 'UPTREND']
sell_signals = [s for s in signals if s[1] == 'DOWNTREND']

print('='*60)
print('2026-03-17 交易模拟深度复盘')
print('='*60)

print(f'\n【信号汇总】')
print(f'  买入信号 (UPTREND + BUY_PRESSURE): {len(buy_signals)}只')
print(f'  卖出信号 (DOWNTREND + SELL_PRESSURE): {len(sell_signals)}只')
print(f'  有效信号总计: {len(signals)}只')

print(f'\n【买入信号明细】')
for s in buy_signals:
    print(f'  {s[0]:6s} | ${s[3]:8.2f} | {s[2]}')

print(f'\n【卖出信号明细】')
for s in sell_signals:
    print(f'  {s[0]:6s} | ${s[3]:8.2f} | {s[2]}')

# 风控分析
print(f'\n【风控参数】')
print('  - 止损: 2R (2倍风险)')
print('  - 止盈: 3R-4R (3-4倍风险)')
print('  - 单笔风险: 1-2% 仓位')
print('  - 最大仓位: 15%')

# 统计最近几天的信号趋势
print(f'\n【历史对比】')
for day in ['2026-03-14', '2026-03-15', '2026-03-16', '2026-03-17']:
    c.execute(f"SELECT COUNT(*) FROM trades WHERE date LIKE '{day}%' AND ((trend='UPTREND' AND ob_signal='BUY_PRESSURE') OR (trend='DOWNTREND' AND ob_signal='SELL_PRESSURE'))")
    count = c.fetchone()[0]
    c.execute(f"SELECT COUNT(DISTINCT stock) FROM trades WHERE date LIKE '{day}%'")
    stocks = c.fetchone()[0]
    print(f'  {day}: {count}信号 / {stocks}只股票')

conn.close()
