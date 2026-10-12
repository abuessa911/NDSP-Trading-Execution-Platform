// DEMO DATA ONLY. Centralised, removable, never sourced from an API or exchange.
import type { AccountSummary, Alert, AuditEvent, HealthNode, Market, Order, Position, RiskStatus, SessionRow, Signal, Strategy, Trade } from "../types";

export const DEMO_STAMP = "DEMO DATA · NOT CONNECTED · READ-ONLY UI PREVIEW";
const wave = (seed: number, n = 24) => Array.from({ length: n }, (_, i) => 50 + Math.sin(i / 3 + seed) * 14 + Math.cos(i / 1.7 + seed * 2) * 8 + i * (seed % 2 ? 0.5 : -0.4));

export const account: AccountSummary = { balance: 48210.35, available: 31884.1, margin: 16326.25, unrealized: 412.77, realized: 1893.4, daily: 236.18, weekly: 1104.52 };
export const markets: Market[] = [
  { id: "m1", symbol: "BTCUSDT", price: 64218.4, change24h: 1.84, volume: "2.41B", volatility: 38, bot: "Trading", strategy: "Trend Ladder", timeframe: "1h", signal: "Buy", position: "Open", spark: wave(1) },
  { id: "m2", symbol: "ETHUSDT", price: 3142.65, change24h: -0.72, volume: "1.12B", volatility: 44, bot: "Trading", strategy: "Range Fade", timeframe: "15m", signal: "Sell", position: "Open", spark: wave(2) },
  { id: "m3", symbol: "SOLUSDT", price: 148.92, change24h: 4.31, volume: "684M", volatility: 71, bot: "Watching", strategy: "Breakout Scout", timeframe: "4h", signal: "Buy", position: "None", spark: wave(3) },
  { id: "m4", symbol: "BNBUSDT", price: 587.3, change24h: 0.41, volume: "212M", volatility: 29, bot: "Idle", strategy: "Unassigned", timeframe: "1h", signal: "Neutral", position: "None", spark: wave(4) },
  { id: "m5", symbol: "XRPUSDT", price: 0.5231, change24h: -2.18, volume: "398M", volatility: 52, bot: "Watching", strategy: "Range Fade", timeframe: "30m", signal: "Neutral", position: "None", spark: wave(5) },
  { id: "m6", symbol: "ADAUSDT", price: 0.4476, change24h: -1.04, volume: "121M", volatility: 47, bot: "Idle", strategy: "Unassigned", timeframe: "1h", signal: "Neutral", position: "None", spark: wave(6) },
  { id: "m7", symbol: "DOGEUSDT", price: 0.1583, change24h: 6.92, volume: "507M", volatility: 83, bot: "Watching", strategy: "Breakout Scout", timeframe: "5m", signal: "Buy", position: "None", spark: wave(7) },
  { id: "m8", symbol: "LINKUSDT", price: 14.27, change24h: 2.06, volume: "96M", volatility: 41, bot: "Trading", strategy: "Mean Return", timeframe: "1h", signal: "Buy", position: "Open", spark: wave(8) },
];
export const positions: Position[] = [
  { id: "p1", symbol: "BTCUSDT", side: "LONG", size: 0.184, entry: 62940.1, mark: 64218.4, leverage: 3, margin: 3851.2, pnl: 235.2, stop: 61200, target: 67500, strategy: "Trend Ladder", timeframe: "1h", opened: "2h 14m ago", status: "Protected" },
  { id: "p2", symbol: "ETHUSDT", side: "SHORT", size: 2.6, entry: 3189.4, mark: 3142.65, leverage: 2, margin: 4146.2, pnl: 121.55, stop: 3260, target: 2980, strategy: "Range Fade", timeframe: "15m", opened: "47m ago", status: "Protected" },
  { id: "p3", symbol: "LINKUSDT", side: "LONG", size: 310, entry: 14.41, mark: 14.27, leverage: 2, margin: 2233.9, pnl: -43.4, stop: 0, target: 15.6, strategy: "Mean Return", timeframe: "1h", opened: "6h 02m ago", status: "Unprotected" },
];
export const orders: Order[] = [
  { id: "ORD-30417", symbol: "BTCUSDT", side: "BUY", type: "LIMIT", qty: 0.05, price: 63800, filled: 0, status: "Open", strategy: "Trend Ladder", created: "09:42:11", updated: "09:42:11", note: "Ladder rung 2 of 3." },
  { id: "ORD-30416", symbol: "ETHUSDT", side: "SELL", type: "MARKET", qty: 2.6, price: 3189.4, filled: 2.6, status: "Filled", strategy: "Range Fade", created: "09:03:55", updated: "09:03:56", note: "Filled in a single execution." },
  { id: "ORD-30415", symbol: "SOLUSDT", side: "BUY", type: "LIMIT", qty: 40, price: 141.2, filled: 0, status: "Cancelled", strategy: "Breakout Scout", created: "08:51:20", updated: "08:58:02", note: "Signal expired before price was reached." },
  { id: "ORD-30414", symbol: "DOGEUSDT", side: "BUY", type: "MARKET", qty: 90000, price: 0.1583, filled: 0, status: "Rejected", strategy: "Breakout Scout", created: "08:40:09", updated: "08:40:09", note: "Rejected by risk gate: symbol limit exceeded." },
  { id: "ORD-30413", symbol: "LINKUSDT", side: "BUY", type: "LIMIT", qty: 310, price: 14.41, filled: 310, status: "Filled", strategy: "Mean Return", created: "03:40:14", updated: "03:41:48", note: "Filled in 2 parts." },
  { id: "ORD-30412", symbol: "BTCUSDT", side: "BUY", type: "LIMIT", qty: 0.184, price: 62940.1, filled: 0.184, status: "Filled", strategy: "Trend Ladder", created: "07:28:31", updated: "07:28:33", note: "Rung 1 of 3." },
];
export const trades: Trade[] = [
  { id: "t1", symbol: "BTCUSDT", direction: "LONG", entry: 61100, exit: 62480, qty: 0.2, pnl: 276, fees: 6.2, strategy: "Trend Ladder", timeframe: "1h", opened: "Mon 04:10", closed: "Mon 11:35", duration: "7h 25m", result: "Win" },
  { id: "t2", symbol: "ETHUSDT", direction: "SHORT", entry: 3240, exit: 3281, qty: 2, pnl: -82, fees: 3.1, strategy: "Range Fade", timeframe: "15m", opened: "Mon 13:02", closed: "Mon 14:20", duration: "1h 18m", result: "Loss" },
  { id: "t3", symbol: "SOLUSDT", direction: "LONG", entry: 139.4, exit: 146.8, qty: 30, pnl: 222, fees: 2.4, strategy: "Breakout Scout", timeframe: "4h", opened: "Tue 02:00", closed: "Tue 18:00", duration: "16h", result: "Win" },
  { id: "t4", symbol: "LINKUSDT", direction: "LONG", entry: 14.9, exit: 14.52, qty: 280, pnl: -106.4, fees: 1.9, strategy: "Mean Return", timeframe: "1h", opened: "Wed 06:00", closed: "Wed 09:40", duration: "3h 40m", result: "Loss" },
  { id: "t5", symbol: "BTCUSDT", direction: "SHORT", entry: 65020, exit: 64110, qty: 0.15, pnl: 136.5, fees: 4.8, strategy: "Range Fade", timeframe: "30m", opened: "Wed 15:15", closed: "Wed 20:45", duration: "5h 30m", result: "Win" },
  { id: "t6", symbol: "ETHUSDT", direction: "LONG", entry: 3050, exit: 3118, qty: 3, pnl: 204, fees: 3.7, strategy: "Trend Ladder", timeframe: "1h", opened: "Thu 05:00", closed: "Thu 13:10", duration: "8h 10m", result: "Win" },
];
export const strategies: Strategy[] = [
  { id: "s1", name: "Trend Ladder", state: "Active", markets: ["BTCUSDT", "ETHUSDT"], timeframe: "1h", risk: 32, lastSignal: "Buy BTCUSDT · 09:41", trades: 58, winRate: 57.4, pnl: 1284.6, updated: "4m ago", note: "Scales into trends in three rungs with a trailing protective stop." },
  { id: "s2", name: "Range Fade", state: "Active", markets: ["ETHUSDT", "XRPUSDT", "BTCUSDT"], timeframe: "15m", risk: 24, lastSignal: "Sell ETHUSDT · 09:03", trades: 133, winRate: 51.9, pnl: 402.1, updated: "1m ago", note: "Fades range extremes when volatility compresses." },
  { id: "s3", name: "Breakout Scout", state: "Paused", markets: ["SOLUSDT", "DOGEUSDT"], timeframe: "4h", risk: 18, lastSignal: "Buy SOLUSDT · 08:50", trades: 41, winRate: 46.3, pnl: -118.9, updated: "52m ago", note: "Paused by operator pending volatility review." },
  { id: "s4", name: "Mean Return", state: "Disabled", markets: ["LINKUSDT"], timeframe: "1h", risk: 8, lastSignal: "Buy LINKUSDT · 03:40", trades: 27, winRate: 55.6, pnl: 96.3, updated: "6h ago", note: "Disabled by default; one open position remains from the last run." },
];
export const signals: Signal[] = [
  { id: "g1", time: "09:41:07", symbol: "BTCUSDT", timeframe: "1h", strategy: "Trend Ladder", direction: "Buy", price: 64102, stage: "Executed", evidence: ["EMA 20 crossed above EMA 50", "Volume 1.4x of 20-bar mean", "Higher-timeframe trend aligned"], action: "Limit order ORD-30417 placed (demo)." },
  { id: "g2", time: "09:03:52", symbol: "ETHUSDT", timeframe: "15m", strategy: "Range Fade", direction: "Sell", price: 3189.4, stage: "Completed", evidence: ["Price tagged range high twice", "RSI 71 and diverging"], action: "Position opened and protected." },
  { id: "g3", time: "08:50:40", symbol: "SOLUSDT", timeframe: "4h", strategy: "Breakout Scout", direction: "Buy", price: 141.2, stage: "Expired", evidence: ["Breakout candidate above 140.8"], action: "No entry; signal window elapsed." },
  { id: "g4", time: "08:40:08", symbol: "DOGEUSDT", timeframe: "5m", strategy: "Breakout Scout", direction: "Buy", price: 0.1583, stage: "Blocked", evidence: ["Momentum burst", "Volatility 83 above ceiling"], action: "Blocked: symbol exposure limit." },
  { id: "g5", time: "09:44:30", symbol: "LINKUSDT", timeframe: "1h", strategy: "Mean Return", direction: "Buy", price: 14.27, stage: "Validating", evidence: ["Price 1.9 sigma below mean"], action: "Awaiting risk and policy checks." },
  { id: "g6", time: "09:45:02", symbol: "XRPUSDT", timeframe: "30m", strategy: "Range Fade", direction: "Sell", price: 0.5231, stage: "Detected", evidence: ["Rejection wick at resistance"], action: "Queued for validation." },
];
export const alerts: Alert[] = [
  { id: "a1", time: "09:44", severity: "Critical", category: "Exchange", title: "Exchange link degraded", message: "Order acknowledgement latency exceeded the threshold for 3 consecutive checks.", subject: "Binance" },
  { id: "a2", time: "09:12", severity: "Warning", category: "Risk", title: "Daily loss at 62% of limit", message: "Remaining capacity is 38%. New entries are throttled.", subject: "Account" },
  { id: "a3", time: "08:40", severity: "Warning", category: "Trading", title: "Order rejected by risk gate", message: "ORD-30414 exceeded the DOGEUSDT symbol limit.", subject: "DOGEUSDT" },
  { id: "a4", time: "08:21", severity: "Warning", category: "Risk", title: "Position without stop", message: "LINKUSDT long has no protective stop configured.", subject: "LINKUSDT" },
  { id: "a5", time: "07:58", severity: "Information", category: "Strategy", title: "Breakout Scout paused", message: "Paused by operator.", subject: "Breakout Scout" },
  { id: "a6", time: "07:10", severity: "Information", category: "System", title: "Market data resynchronised", message: "Gap of 4 seconds recovered.", subject: "Market data" },
  { id: "a7", time: "06:02", severity: "Information", category: "Security", title: "New session established", message: "Sign-in from a known device.", subject: "Account" },
];
export const risk: RiskStatus = { exposure: 41, dailyLoss: 620, maxDailyLoss: 1000, utilization: 62, openPositions: 3, maxPositions: 5, warnings: ["Daily loss above 60% of limit", "LINKUSDT has no stop"], blocked: ["DOGEUSDT entries: symbol limit", "New leverage above 3x"], bySymbol: [{ symbol: "BTCUSDT", pct: 46 }, { symbol: "ETHUSDT", pct: 31 }, { symbol: "LINKUSDT", pct: 23 }], byStrategy: [{ name: "Trend Ladder", pct: 46 }, { name: "Range Fade", pct: 31 }, { name: "Mean Return", pct: 23 }] };
export const healthNodes: HealthNode[] = [
  { id: "h1", name: "API", status: "Operational", metric: "38 ms", detail: "Last check 12 s ago" },
  { id: "h2", name: "Exchange", status: "Degraded", metric: "412 ms", detail: "Order ack slow; sync lag 3 s" },
  { id: "h3", name: "Database", status: "Operational", metric: "4 ms", detail: "Primary healthy" },
  { id: "h4", name: "Market data", status: "Operational", metric: "0.8 s", detail: "Freshness within bounds" },
  { id: "h5", name: "Trading worker", status: "Operational", metric: "idle 2 s", detail: "Queue depth 0" },
  { id: "h6", name: "Strategy engine", status: "Operational", metric: "4 loaded", detail: "2 active" },
  { id: "h7", name: "Risk engine", status: "Operational", metric: "62% used", detail: "Gate evaluating" },
  { id: "h8", name: "Notifications", status: "Down", metric: "no heartbeat", detail: "Channel not configured" },
];
export const audit: AuditEvent[] = [
  { id: "e1", time: "09:41", event: "Signal detected", category: "Signal", severity: "Information", actor: "Trend Ladder" },
  { id: "e2", time: "09:12", event: "Risk block", category: "Risk", severity: "Warning", actor: "Risk engine" },
  { id: "e3", time: "07:58", event: "Strategy paused", category: "Strategy", severity: "Information", actor: "Operator" },
  { id: "e4", time: "06:02", event: "Login", category: "Security", severity: "Information", actor: "Operator" },
];
export const sessions: SessionRow[] = [
  { id: "x1", device: "Desktop browser", location: "Riyadh", seen: "now", current: true },
  { id: "x2", device: "Mobile browser", location: "Riyadh", seen: "3h ago", current: false },
];
export const equitySeries = Array.from({ length: 60 }, (_, i) => 46000 + i * 38 + Math.sin(i / 4) * 420 + Math.cos(i / 9) * 260);
export const dailyPnl = [120, -64, 210, 88, -142, 301, 236, -38, 174, 96, -210, 262, 144, 236];
export const timelineSteps = ["Strategy signal", "Decision contract", "Risk gate", "Policy check", "Order", "Fills", "Result"];
export const traceNotes = ["Trend Ladder detected an EMA cross.", "Contract wrapper accepted (demo, unsigned).", "Passed: exposure 41%, daily loss 62%.", "Policy: simulation mode permits entry in this scripted example only.", "Limit order ORD-30417 prepared.", "No fills yet.", "Pending."];
export const replaySeries = Array.from({ length: 50 }, (_, i) => 100 + Math.sin(i / 5) * 12 + i * 0.4);
export const strategySketch = [0, 40, 22, 80, 60, 130, 118, 190];
