#!/usr/bin/env bash
set -e

cd /home/nawaf511/ndsp-binance-bot

STAMP="$(date +%Y%m%d_%H%M%S)"
BACKUP_DIR=".backup_csv_cleanup_$STAMP"
mkdir -p "$BACKUP_DIR"

cp backend/app/api/advanced_routes.py "$BACKUP_DIR/advanced_routes.py"
cp frontend/app/logs/page.tsx "$BACKUP_DIR/logs_page.tsx"
cp frontend/app/globals.css "$BACKUP_DIR/globals.css"

echo "✅ Backup created: $BACKUP_DIR"

python3 - <<'PY'
from pathlib import Path

p = Path("backend/app/api/advanced_routes.py")
s = p.read_text()

if "import csv" not in s:
    s = "import csv\nimport io\nfrom datetime import datetime, timedelta\nfrom fastapi.responses import StreamingResponse\n" + s

if "class CleanupLogsRequest" not in s:
    s = s.replace(
        "class AdminUserUpdate(BaseModel):",
        '''
class CleanupLogsRequest(BaseModel):
    older_than_days: int = Field(default=30, ge=1, le=3650)
    rejected_only: bool = False


class AdminUserUpdate(BaseModel):'''
    )

if '@router.get("/system/logs/export.csv")' not in s:
    s += r'''

@router.get("/system/logs/export.csv")
def export_trades_csv(
    rejected_only: bool = False,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    query = db.query(TradeLog).filter(TradeLog.user_id == user.id)

    if rejected_only:
        query = query.filter(TradeLog.status.in_(["rejected", "failed", "error"]))

    rows = query.order_by(TradeLog.id.desc()).limit(5000).all()

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow([
        "id",
        "symbol",
        "side",
        "amount",
        "price",
        "notional_usdt",
        "pnl_usdt",
        "stop_loss_price",
        "take_profit_price",
        "protective_orders_status",
        "status",
        "mode",
        "reason",
        "created_at",
    ])

    for x in rows:
        writer.writerow([
            x.id,
            x.symbol,
            x.side,
            x.amount,
            x.price,
            x.notional_usdt,
            getattr(x, "pnl_usdt", 0),
            getattr(x, "stop_loss_price", 0),
            getattr(x, "take_profit_price", 0),
            getattr(x, "protective_orders_status", "preview"),
            x.status,
            x.mode,
            x.reason,
            x.created_at,
        ])

    output.seek(0)

    filename = "rejected_trades.csv" if rejected_only else "trades.csv"

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        }
    )


@router.post("/system/logs/cleanup")
def cleanup_logs(
    payload: CleanupLogsRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    cutoff = datetime.utcnow() - timedelta(days=payload.older_than_days)

    query = (
        db.query(TradeLog)
        .filter(TradeLog.user_id == user.id)
        .filter(TradeLog.created_at < cutoff)
    )

    if payload.rejected_only:
        query = query.filter(TradeLog.status.in_(["rejected", "failed", "error"]))

    count = query.count()
    query.delete(synchronize_session=False)
    db.commit()

    return {
        "status": "cleaned",
        "deleted": count,
        "older_than_days": payload.older_than_days,
        "rejected_only": payload.rejected_only,
    }
'''
p.write_text(s)
print("✅ advanced_routes.py export/cleanup endpoints added")
PY

cat > frontend/app/logs/page.tsx <<'EOF'
"use client";

import { useEffect, useState } from "react";
import { api, getToken } from "../../lib/api";

export default function LogsPage() {
  const [summary, setSummary] = useState<any>(null);
  const [rejections, setRejections] = useState<any[]>([]);
  const [trades, setTrades] = useState<any[]>([]);
  const [mode, setMode] = useState<"rejections" | "all">("rejections");
  const [message, setMessage] = useState("");
  const [cleanupDays, setCleanupDays] = useState(30);
  const [cleanupRejectedOnly, setCleanupRejectedOnly] = useState(false);

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

  async function downloadCsv(rejectedOnly: boolean) {
    setMessage("");
    try {
      const token = getToken();
      const res = await fetch(`/api/system/logs/export.csv?rejected_only=${rejectedOnly}`, {
        headers: {
          Authorization: `Bearer ${token}`
        }
      });

      if (!res.ok) {
        const txt = await res.text();
        throw new Error(txt);
      }

      const blob = await res.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = rejectedOnly ? "rejected_trades.csv" : "trades.csv";
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch (e: any) {
      setMessage("فشل تصدير CSV: " + e.message);
    }
  }

  async function cleanupLogs() {
    setMessage("");

    const ok = window.confirm(
      `هل أنت متأكد من تنظيف السجلات الأقدم من ${cleanupDays} يوم؟`
    );
    if (!ok) return;

    try {
      const data = await api("/system/logs/cleanup", {
        method: "POST",
        body: JSON.stringify({
          older_than_days: cleanupDays,
          rejected_only: cleanupRejectedOnly
        })
      });

      setMessage(`تم حذف ${data.deleted} سجل`);
      await loadLogs();
    } catch (e: any) {
      setMessage("فشل تنظيف السجلات: " + e.message);
    }
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

        <div className="card logs-tools">
          <h2>أدوات السجلات</h2>

          <div className="logs-actions">
            <button className="btn btn-primary" onClick={() => downloadCsv(false)}>
              تصدير كل الصفقات CSV
            </button>

            <button className="btn btn-secondary" onClick={() => downloadCsv(true)}>
              تصدير المرفوضة CSV
            </button>
          </div>

          <div className="cleanup-box">
            <h3>تنظيف السجلات القديمة</h3>

            <label>احذف السجلات الأقدم من عدد أيام</label>
            <input
              className="input"
              type="number"
              value={cleanupDays}
              onChange={e => setCleanupDays(Number(e.target.value))}
            />

            <label className="cleanup-check">
              <input
                type="checkbox"
                checked={cleanupRejectedOnly}
                onChange={e => setCleanupRejectedOnly(e.target.checked)}
              />
              حذف المرفوضة فقط
            </label>

            <button className="btn btn-danger" onClick={cleanupLogs}>
              تنظيف السجلات
            </button>
          </div>
        </div>

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
