import sqlite3
from collections import defaultdict

conn = sqlite3.connect('C:/Users/Administrator/Documents/Playground/Trend_OB_AI/trades.db')
c = conn.cursor()

print('='*60)
print('自我进化分析')
print('='*60)

# 1. 分析信号频率 vs 实际走势
c.execute("""
    SELECT stock, trend, ob_signal, last_price, date
    FROM trades
    WHERE date LIKE '2026-03-17%' OR date LIKE '2026-03-29%'
    ORDER BY stock, date
""")

# 按股票分组
stock_signals = defaultdict(list)
for r in c.fetchall():
    stock_signals[r[0]].append(r)

print('\n【信号一致性分析】')
consistent = 0
inconsistent = 0
for stock, signals in stock_signals.items():
    if len(signals) >= 2:
        trends = [s[1] for s in signals]
        if trends[0] == trends[-1]:
            consistent += 1
        else:
            inconsistent += 1
            
print('  信号稳定: %d只' % consistent)
print('  信号变化: %d只' % inconsistent)

# 2. 分析哪些信号产生了交易
c.execute('SELECT DISTINCT symbol FROM paper_orders')
traded = [r[0] for r in c.fetchall()]

c.execute("""
    SELECT stock, trend, ob_signal
    FROM trades
    WHERE date LIKE '2026-03-17%'
    AND ((trend='UPTREND' AND ob_signal='BUY_PRESSURE') OR (trend='DOWNTREND' AND ob_signal='SELL_PRESSURE'))
    GROUP BY stock
""")
signal_stocks = [r[0] for r in c.fetchall()]

print('\n【信号转化率】')
print('  有效信号: %d只' % len(signal_stocks))
print('  实际交易: %d只' % len(traded))
print('  转化率: %.1f%%' % (len(traded)/len(signal_stocks)*100))

# 3. 持仓时间分析
c.execute("""
    SELECT symbol, ts, action
    FROM paper_orders
    WHERE action = 'BUY'
    ORDER BY ts
""")
buy_times = {}
for r in c.fetchall():
    buy_times[r[0]] = r[1]

print('\n【持仓时长】')
for stock, ts in buy_times.items():
    print('  %s: 买入于 %s' % (stock, ts))

# 4. 提取最佳信号特征
print('\n【盈利交易特征】')
c.execute("""
    SELECT o.symbol, t.trend, t.ob_signal, o.price as buy_price, o2.price as sell_price, o2.realized_pnl
    FROM paper_orders o
    JOIN paper_orders o2 ON o.symbol = o2.symbol AND o.action = 'BUY' AND o2.action = 'SELL'
    JOIN trades t ON t.stock = o.symbol
    WHERE o.ts < o2.ts
    ORDER BY o2.realized_pnl DESC
""")
for r in c.fetchall():
    print('  %s: %s+%s | 买入$%.2f 卖出$%.2f 盈亏$%.2f' % (r[0], r[1], r[2], r[3], r[4], r[5]))

# 5. 建议
print('\n【自我进化建议】')
print('  1. 考虑增加移动止损而不是固定止损')
print('  2. 添加趋势反转确认信号')
print('  3. 设置最大持仓时间限制(如5天)')
print('  4. 增加RSI/MACD等技术过滤')
print('  5. 分析趋势持续时间过滤')

conn.close()