#!/usr/bin/env bash
set -e

cd /home/nawaf511/ndsp-binance-bot

STAMP="$(date +%Y%m%d_%H%M%S)"
BACKUP_DIR=".backup_logs_center_$STAMP"
mkdir -p "$BACKUP_DIR"

cp backend/app/api/advanced_routes.py "$BACKUP_DIR/advanced_routes.py"
cp frontend/app/page.tsx "$BACKUP_DIR/page.tsx"
cp frontend/app/globals.css "$BACKUP_DIR/globals.css"

echo "✅ Backup created: $BACKUP_DIR"

mkdir -p frontend/app/logs

python3 - <<'PY'
from pathlib import Path

p = Path("backend/app/api/advanced_routes.py")
s = p.read_text()

if '@router.get("/system/logs/rejections")' not in s:
    s += r'''

@router.get("/system/logs/rejections")
def rejected_trades_log(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    rows = (
        db.query(TradeLog)
        .filter(TradeLog.user_id == user.id)
        .filter(TradeLog.status.in_(["rejected", "failed", "error"]))
        .order_by(TradeLog.id.desc())
        .limit(150)
        .all()
    )

    return [
        {
            "id": x.id,
            "symbol": x.symbol,
            "side": x.side,
            "amount": x.amount,
            "price": x.price,
            "notional_usdt": x.notional_usdt,
            "status": x.status,
            "mode": x.mode,
            "reason": x.reason,
            "exchange_response": x.exchange_response,
            "created_at": x.created_at,
        }
        for x in rows
    ]


@router.get("/system/logs/trades")
def trades_log_extended(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    rows = (
        db.query(TradeLog)
        .filter(TradeLog.user_id == user.id)
        .order_by(TradeLog.id.desc())
        .limit(200)
        .all()
    )

    return [
        {
            "id": x.id,
            "symbol": x.symbol,
            "side": x.side,
            "amount": x.amount,
            "price": x.price,
            "notional_usdt": x.notional_usdt,
            "pnl_usdt": getattr(x, "pnl_usdt", 0),
            "stop_loss_price": getattr(x, "stop_loss_price", 0),
            "take_profit_price": getattr(x, "take_profit_price", 0),
            "protective_orders_status": getattr(x, "protective_orders_status", "preview"),
            "status": x.status,
            "mode": x.mode,
            "reason": x.reason,
            "exchange_response": x.exchange_response,
            "created_at": x.created_at,
        }
        for x in rows
    ]


@router.get("/system/logs/summary")
def logs_summary(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    rows = (
        db.query(TradeLog)
        .filter(TradeLog.user_id == user.id)
        .order_by(TradeLog.id.desc())
        .limit(500)
        .all()
    )

    total = len(rows)
    rejected = len([x for x in rows if x.status in ["rejected", "failed", "error"]])
    closed = len([x for x in rows if x.status == "closed"])
    simulated = len([x for x in rows if x.status == "simulated"])

    return {
        "total": total,
        "closed": closed,
        "simulated": simulated,
        "rejected_or_failed": rejected,
        "latest_status": rows[0].status if rows else None,
        "latest_reason": rows[0].reason if rows else None,
    }
'''
p.write_text(s)
print("✅ advanced_routes.py logs endpoints added")
PY

cat > frontend/app/logs/page.tsx <<'EOF'
"use client";

import { useEffect, useState } from "react";
import { api } from "../../lib/api";

export default function LogsPage() {
  const [summary, setSummary] = useState<any>(null);
  const [rejections, setRejections] = useState<any[]>([]);
  const [trades, setTrades] = useState<any[]>([]);
  const [mode, setMode] = useState<"rejections" | "all">("rejections");
  const [message, setMessage] = useState("");

  async function loadLogs() {
    setMessage("");
    try {
      const s = await api("/system/logs/summary");
      const r = await api("/system/logs/rejections");
      const t = await api("/system/logs/trades");

      setSummary(s);
      setRejections(r);
      setTrades(t);
    } catch (e: any) {
      setMessage("فشل تحميل السجلات: " + e.message);
    }
  }

  useEffect(() => {
    loadLogs();
  }, []);

  const rows = mode === "rejections" ? rejections : trades;

  function statusClass(status: string) {
    if (status === "closed" || status === "simulated") return "log-badge ok";
    if (status === "rejected" || status === "failed" || status === "error") return "log-badge bad";
    return "log-badge neutral";
  }

  return (
    <main className="container">
      <div className="card">
        <h1>Logs Center</h1>
        <p>مركز متابعة الإشارات، الصفقات، وأسباب الرفض.</p>

        {message && <div className="card">{message}</div>}

        {summary && (
          <div className="logs-summary-grid">
            <div className="logs-summary-box">
              <span>Total</span>
              <strong>{summary.total}</strong>
            </div>
            <div className="logs-summary-box">
              <span>Closed</span>
              <strong>{summary.closed}</strong>
            </div>
            <div className="logs-summary-box">
              <span>Simulated</span>
              <strong>{summary.simulated}</strong>
            </div>
            <div className="logs-summary-box danger">
              <span>Rejected / Failed</span>
              <strong>{summary.rejected_or_failed}</strong>
            </div>
          </div>
        )}

        <div className="logs-actions">
          <button className={mode === "rejections" ? "btn btn-primary" : "btn btn-secondary"} onClick={() => setMode("rejections")}>
            المرفوضة فقط
          </button>

          <button className={mode === "all" ? "btn btn-primary" : "btn btn-secondary"} onClick={() => setMode("all")}>
            كل السجلات
          </button>

          <button className="btn btn-secondary" onClick={loadLogs}>
            تحديث
          </button>
        </div>

        <div className="logs-list">
          {rows.map((x) => (
            <div className="log-item" key={x.id}>
              <div className="log-item-header">
                <div>
                  <strong>#{x.id} - {x.symbol} / {x.side}</strong>
                  <p>{x.created_at}</p>
                </div>

                <div className="log-badges">
                  <span className={statusClass(x.status)}>{x.status}</span>
                  <span className="log-badge mode">{x.mode}</span>
                </div>
              </div>

              <div className="log-item-grid">
                <div>
                  <span>Amount</span>
                  <strong>{x.amount}</strong>
                </div>
                <div>
                  <span>Price</span>
                  <strong>{x.price}</strong>
                </div>
                <div>
                  <span>USDT</span>
                  <strong>{x.notional_usdt}</strong>
                </div>
                <div>
                  <span>SL</span>
                  <strong>{x.stop_loss_price || 0}</strong>
                </div>
                <div>
                  <span>TP</span>
                  <strong>{x.take_profit_price || 0}</strong>
                </div>
                <div>
                  <span>Protective</span>
                  <strong>{x.protective_orders_status || "preview"}</strong>
                </div>
              </div>

              <div className="log-reason">
                <span>Reason</span>
                <p>{x.reason || "—"}</p>
              </div>

              {x.exchange_response && (
                <details className="log-details">
                  <summary>Exchange Response</summary>
                  <pre>{x.exchange_response}</pre>
                </details>
              )}
            </div>
          ))}

          {rows.length === 0 && (
            <div className="card">
              لا توجد سجلات في هذا القسم.
            </div>
          )}
        </div>

        <p style={{ marginTop: 22 }}>
          <a href="/">العودة للوحة التحكم</a>
        </p>
      </div>
    </main>
  );
}
