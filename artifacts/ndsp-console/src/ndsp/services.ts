// Replaceable frontend adapters. Each resolves DEMO data; swap the body for a real API call once one exists.
import * as d from "./mocks/demo-data";
const later = <T,>(v: T, ms = 450) => new Promise<T>(r => setTimeout(() => r(v), ms));
export const marketService = { list: () => later(d.markets) };
export const positionService = { list: () => later(d.positions) };
export const orderService = { list: () => later(d.orders) };
export const tradeService = { list: () => later(d.trades) };
export const strategyService = { list: () => later(d.strategies) };
export const signalService = { list: () => later(d.signals) };
export const riskService = { get: () => later(d.risk) };
export const analyticsService = { equity: () => later({ equity: d.equitySeries, daily: d.dailyPnl, trades: d.trades }) };
export const alertService = { list: () => later(d.alerts) };
export const healthService = { nodes: () => later(d.healthNodes) };
export const accountService = { summary: () => later(d.account) };
export const auditService = { list: () => later(d.audit) };
export const securityService = { sessions: () => later(d.sessions) };
export const dashboardService = { snapshot: () => later({ account: d.account, markets: d.markets, risk: d.risk, signals: d.signals }) };
