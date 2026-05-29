#!/usr/bin/env bash
set -e

cd /home/nawaf511/ndsp-binance-bot

PAGE="frontend/app/page.tsx"

if [ ! -f "$PAGE" ]; then
  echo "❌ لم أجد الملف: $PAGE"
  exit 1
fi

cp "$PAGE" "$PAGE.backup_$(date +%Y%m%d_%H%M%S)"

python3 - <<'PY'
from pathlib import Path

p = Path("frontend/app/page.tsx")
s = p.read_text()

insert_func = r'''
  function formatDate(value: string) {
    if (!value) return "-";
    try {
      return new Date(value).toLocaleString("ar-SA", {
        year: "numeric",
        month: "2-digit",
        day: "2-digit",
        hour: "2-digit",
        minute: "2-digit"
      });
    } catch {
      return value;
    }
  }

  function LastTradeCard({ trade }: { trade: any }) {
    if (!trade) {
      return (
        <div className="card">
          <h2>آخر صفقة</h2>
          <p style={{ color: "#94a3b8" }}>لا توجد صفقات بعد.</p>
        </div>
      );
    }

    const isBuy = trade.side === "BUY";
    const isClosed = trade.status === "closed";

    return (
      <div className="card last-trade-card">
        <div className="last-trade-header">
          <div>
            <h2 style={{ margin: 0 }}>آخر صفقة</h2>
            <p style={{ margin: "8px 0 0", color: "#94a3b8" }}>
              رقم الصفقة #{trade.id}
            </p>
          </div>

          <div className="last-trade-badges">
            <span className={isBuy ? "trade-badge buy" : "trade-badge sell"}>
              {trade.side}
            </span>
            <span className={isClosed ? "trade-badge closed" : "trade-badge neutral"}>
              {trade.status}
            </span>
            <span className="trade-badge mode">
              {trade.mode}
            </span>
          </div>
        </div>

        <div className="trade-summary">
          <div className="trade-main-symbol">
            <span>زوج التداول</span>
            <strong>{trade.symbol}</strong>
          </div>

          <div className="trade-main-value">
            <span>القيمة</span>
            <strong>{trade.notional_usdt} USDT</strong>
          </div>
        </div>

        <div className="trade-details-grid">
          <div className="trade-detail-item">
            <span>الكمية</span>
            <strong>{trade.amount}</strong>
          </div>

          <div className="trade-detail-item">
            <span>السعر</span>
            <strong>{trade.price}</strong>
          </div>

          <div className="trade-detail-item">
            <span>الوقت</span>
            <strong>{formatDate(trade.created_at)}</strong>
          </div>

          <div className="trade-detail-item">
            <span>الوضع</span>
            <strong>{trade.mode}</strong>
          </div>
        </div>

        <div className="trade-reason">
          <span>سبب الصفقة</span>
          <p>{trade.reason || "—"}</p>
        </div>
      </div>
    );
  }
'''

# Insert helper component after logout function
marker = '''  function logout() {
    clearToken();
    setMe(null);
    setSettings(null);
    setTrades([]);
    setMessage("تم تسجيل الخروج");
  }
'''

if "function LastTradeCard" not in s:
    if marker not in s:
        raise SystemExit("❌ لم أجد مكان إدراج LastTradeCard")
    s = s.replace(marker, marker + insert_func)

old_block = '''          <div className="card">
            <h2>آخر صفقة</h2>
            {trades[0] ? (
              <pre style={{ whiteSpace: "pre-wrap" }}>{JSON.stringify(trades[0], null, 2)}</pre>
            ) : (
              <p>لا توجد صفقات بعد.</p>
            )}
          </div>
'''

new_block = '''          <LastTradeCard trade={trades[0]} />
'''

if old_block in s:
    s = s.replace(old_block, new_block)
else:
    print("⚠️ لم أجد بلوك آخر صفقة القديم، قد يكون تم تعديله سابقًا.")

p.write_text(s)
print("✅ page.tsx updated")
PY

cat >> frontend/app/globals.css <<'EOF'

/* Improved Last Trade Card */
.last-trade-card {
  background:
    radial-gradient(circle at top left, rgba(34, 197, 94, 0.12), transparent 32%),
    linear-gradient(135deg, #111827 0%, #0f172a 100%);
  border: 1px solid rgba(148, 163, 184, 0.18);
}

.last-trade-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 22px;
}

.last-trade-badges {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.trade-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 999px;
  padding: 8px 12px;
  font-size: 13px;
  font-weight: 800;
  letter-spacing: 0.3px;
}

.trade-badge.buy {
  background: rgba(34, 197, 94, 0.16);
  color: #86efac;
  border: 1px solid rgba(34, 197, 94, 0.25);
}

.trade-badge.sell {
  background: rgba(239, 68, 68, 0.16);
  color: #fecaca;
  border: 1px solid rgba(239, 68, 68, 0.25);
}

.trade-badge.closed {
  background: rgba(59, 130, 246, 0.16);
  color: #bfdbfe;
  border: 1px solid rgba(59, 130, 246, 0.25);
}

.trade-badge.neutral {
  background: rgba(148, 163, 184, 0.16);
  color: #e2e8f0;
  border: 1px solid rgba(148, 163, 184, 0.25);
}

.trade-badge.mode {
  background: rgba(168, 85, 247, 0.16);
  color: #e9d5ff;
  border: 1px solid rgba(168, 85, 247, 0.25);
}

.trade-summary {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
  margin-bottom: 16px;
}

.trade-main-symbol,
.trade-main-value {
  background: rgba(15, 23, 42, 0.78);
  border: 1px solid rgba(148, 163, 184, 0.14);
  border-radius: 18px;
  padding: 18px;
}

.trade-main-symbol span,
.trade-main-value span,
.trade-detail-item span,
.trade-reason span {
  display: block;
  color: #94a3b8;
  font-size: 13px;
  margin-bottom: 8px;
}

.trade-main-symbol strong,
.trade-main-value strong {
  display: block;
  font-size: 28px;
  color: #f8fafc;
}

.trade-details-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
}

.trade-detail-item {
  background: rgba(2, 6, 23, 0.5);
  border: 1px solid rgba(148, 163, 184, 0.12);
  border-radius: 14px;
  padding: 14px;
  min-width: 0;
}

.trade-detail-item strong {
  display: block;
  color: #e5e7eb;
  font-size: 15px;
  word-break: break-word;
}

.trade-reason {
  margin-top: 14px;
  background: rgba(2, 6, 23, 0.5);
  border: 1px solid rgba(148, 163, 184, 0.12);
  border-radius: 14px;
  padding: 14px;
}

.trade-reason p {
  margin: 0;
  color: #f8fafc;
  line-height: 1.7;
  word-break: break-word;
}

@media (max-width: 900px) {
  .last-trade-header {
    flex-direction: column;
  }

  .last-trade-badges {
    justify-content: flex-start;
  }

  .trade-summary,
  .trade-details-grid {
    grid-template-columns: 1fr;
  }

  .trade-main-symbol strong,
  .trade-main-value strong {
    font-size: 24px;
  }
}
