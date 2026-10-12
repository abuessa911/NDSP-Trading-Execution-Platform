import { MarketsView, OrdersView, PositionsView, ReplayView, SignalsView, StrategiesView, TerminalView, TraceView, TradesView } from "./views-trading";
import { ActivityView, AlertsView, AnalyticsView, BotSettingsView, ExchangeView, FutureHealthView, RiskView } from "./OperationsPreview";

export default function PreviewWorkspace({ section }: { section: string }) {
  switch (section) {
    case "markets": return <MarketsView />;
    case "trading": return <TerminalView />;
    case "positions": return <PositionsView />;
    case "orders": return <OrdersView />;
    case "trade-history": return <TradesView />;
    case "strategies": return <StrategiesView />;
    case "ndsp-decisions": return <SignalsView />;
    case "execution-trace": return <TraceView />;
    case "replay-lab": return <ReplayView />;
    case "risk-center": return <RiskView />;
    case "performance": return <AnalyticsView />;
    case "notifications": return <AlertsView />;
    case "binance-connection": return <ExchangeView />;
    case "bot-settings": return <BotSettingsView />;
    case "future-health": return <FutureHealthView />;
    case "activity": return <ActivityView />;
    default: return null;
  }
}
