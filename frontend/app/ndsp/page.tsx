"use client";

import { useEffect, useState } from "react";
import { api } from "../../lib/api";

type NdspPayload = {
  symbol: string;
  notional_usdt: number;
  reason: string;
  ndsp_layer: string;
  decision: {
    direction: string;
    confidence: number;
    grade: string;
    quality_label: string;
    execution_allowed: boolean;
  };
  execution: {
    allowed: boolean;
    mode: string;
  };
  market_alignment: {
    signal: string;
  };
  states: {
    risk_state: string;
    system_state: string;
  };
  explanation: {
    guidance: string;
  };
  side?: string;
};

const safePayload = (): NdspPayload => ({
  symbol: "BTC/USDT",
  notional_usdt: 5,
  reason: "NDSP decision support test",
  ndsp_layer: "layer-1",
  decision: {
    direction: "neutral",
    confidence: 0,
    grade: "F",
    quality_label: "Structurally Invalid",
    execution_allowed: false
  },
  execution: {
    allowed: false,
    mode: "decision_support_only"
  },
  market_alignment: {
    signal: "NO_SIGNAL"
  },
  states: {
    risk_state: "normal",
    system_state: "live"
  },
  explanation: {
    guidance: "Decision-support context only; not a primary execution signal."
  }
});

export default function NdspSignalPage() {
  const [form, setForm] = useState<NdspPayload>(safePayload());
  const [manualSide, setManualSide] = useState("");
  const [message, setMessage] = useState("");
  const [marketType, setMarketType] = useState("spot");
  const [availableSymbols, setAvailableSymbols] = useState<string[]>([]);
  const [symbolsLoading, setSymbolsLoading] = useState(false);

  async function loadSymbols(selectedMarket = "spot") {
    setSymbolsLoading(true);
    try {
      const data = await api(`/symbols/${selectedMarket}`);
      const symbols = Array.isArray(data?.symbols) ? data.symbols : [];
      setAvailableSymbols(symbols);

      if (symbols.length) {
        setForm(prev => ({
          ...prev,
          symbol: symbols.includes(prev.symbol)
            ? prev.symbol
            : (symbols.includes("BTC/USDT") ? "BTC/USDT" : symbols[0])
        }));
      }
    } catch (e: any) {
      setMessage("فشل تحميل قائمة العملات: " + e.message);
    } finally {
      setSymbolsLoading(false);
    }
  }

  useEffect(() => {
    loadSymbols("spot");
  }, []);

  function setDecision(patch: Partial<NdspPayload["decision"]>) {
    setForm(prev => ({ ...prev, decision: { ...prev.decision, ...patch } }));
  }

  function setExecution(patch: Partial<NdspPayload["execution"]>) {
    setForm(prev => ({ ...prev, execution: { ...prev.execution, ...patch } }));
  }

  function setMarketAlignment(patch: Partial<NdspPayload["market_alignment"]>) {
    setForm(prev => ({ ...prev, market_alignment: { ...prev.market_alignment, ...patch } }));
  }

  function setStates(patch: Partial<NdspPayload["states"]>) {
    setForm(prev => ({ ...prev, states: { ...prev.states, ...patch } }));
  }

  async function sendSignal() {
    setMessage("");
    try {
      const payload: NdspPayload = { ...form };

      if (manualSide) {
        payload.side = manualSide;
      } else {
        delete payload.side;
      }

      const data = await api("/ndsp/signal", {
        method: "POST",
        body: JSON.stringify(payload)
      });

      setMessage(
        `نتيجة NDSP: ${data.symbol || form.symbol} / ${data.action || data.side || "NO_ACTION"} / ${data.status || data.trade_status || "unknown"} - ${data.reason || ""}`
      );
    } catch (e: any) {
      setMessage("فشل تنفيذ إشارة NDSP: " + e.message);
    }
  }

  return (
    <main className="container">
      <div className="card">
        <h1>NDSP Signal Bridge</h1>
        <p>هذه الصفحة لاختبار استقبال إشارات NDSP، أما الربط الحقيقي فيكون عبر Webhook آمن.</p>
        <p style={{ color: "#93c5fd" }}>
          NDSP يمكنه إرسال Decision Support Payload كامل بدون BUY/SELL. البوت يقرأ direction داخليًا ثم يقرر BUY / SELL / NO_TRADE.
        </p>

        <div className="card">
          <h2>اختبار داخلي عبر جلسة المستخدم</h2>

          <label>نوع السوق</label>
          <select
            className="input technical-input"
            value={marketType}
            onChange={e => {
              const value = e.target.value;
              setMarketType(value);
              loadSymbols(value);
            }}
          >
            <option value="spot">سبوت Spot</option>
            <option value="futures">عقود آجلة Futures</option>
          </select>

          <label style={{ display: "block", marginTop: 14 }}>العملة</label>
          <select
            className="input technical-input"
            value={form.symbol}
            onChange={e => setForm({ ...form, symbol: e.target.value })}
          >
            {symbolsLoading && <option value={form.symbol}>جاري تحميل العملات...</option>}
            {!symbolsLoading && availableSymbols.length === 0 && <option value={form.symbol}>{form.symbol}</option>}
            {availableSymbols.map(symbol => (
              <option key={symbol} value={symbol}>{symbol}</option>
            ))}
          </select>

          <label style={{ display: "block", marginTop: 14 }}>NDSP Direction</label>
          <select
            className="input"
            value={form.decision.direction}
            onChange={e => setDecision({ direction: e.target.value })}
          >
            <option value="neutral">neutral - لا تداول</option>
            <option value="bullish">bullish - يفسر داخليًا كـ BUY</option>
            <option value="bearish">bearish - يفسر داخليًا كـ SELL</option>
          </select>

          <label style={{ display: "block", marginTop: 14 }}>Confidence</label>
          <input
            className="input"
            type="number"
            value={form.decision.confidence}
            onChange={e => setDecision({ confidence: Number(e.target.value) })}
          />

          <label style={{ display: "block", marginTop: 14 }}>Quality Label</label>
          <select
            className="input"
            value={form.decision.quality_label}
            onChange={e => setDecision({ quality_label: e.target.value })}
          >
            <option value="Structurally Invalid">Structurally Invalid</option>
            <option value="Valid">Valid</option>
          </select>

          <label style={{ display: "block", marginTop: 14 }}>
            <input
              type="checkbox"
              checked={form.decision.execution_allowed}
              onChange={e => setDecision({ execution_allowed: e.target.checked })}
            />{" "}
            decision.execution_allowed
          </label>

          <label style={{ display: "block", marginTop: 14 }}>
            <input
              type="checkbox"
              checked={form.execution.allowed}
              onChange={e => setExecution({ allowed: e.target.checked })}
            />{" "}
            execution.allowed
          </label>

          <label style={{ display: "block", marginTop: 14 }}>market_alignment.signal</label>
          <select
            className="input"
            value={form.market_alignment.signal}
            onChange={e => setMarketAlignment({ signal: e.target.value })}
          >
            <option value="NO_SIGNAL">NO_SIGNAL</option>
            <option value="CONTINUATION_SIGNAL">CONTINUATION_SIGNAL</option>
            <option value="REVERSAL_SIGNAL">REVERSAL_SIGNAL</option>
            <option value="TESTING_ZONE">TESTING_ZONE</option>
          </select>

          <label style={{ display: "block", marginTop: 14 }}>states.risk_state</label>
          <select
            className="input"
            value={form.states.risk_state}
            onChange={e => setStates({ risk_state: e.target.value })}
          >
            <option value="normal">normal</option>
            <option value="paused">paused</option>
            <option value="drawdown">drawdown</option>
            <option value="safe_mode">safe_mode</option>
            <option value="error">error</option>
          </select>

          <label style={{ display: "block", marginTop: 14 }}>Manual side override للاختبار فقط</label>
          <select className="input" value={manualSide} onChange={e => setManualSide(e.target.value)}>
            <option value="">بدون Override - استخدم NDSP decision.direction</option>
            <option value="BUY">BUY</option>
            <option value="SELL">SELL</option>
          </select>

          <label style={{ display: "block", marginTop: 14 }}>Notional USDT</label>
          <input
            className="input"
            type="number"
            value={form.notional_usdt}
            onChange={e => setForm({ ...form, notional_usdt: Number(e.target.value) })}
          />

          <label style={{ display: "block", marginTop: 14 }}>NDSP Layer</label>
          <input className="input" value={form.ndsp_layer} onChange={e => setForm({ ...form, ndsp_layer: e.target.value })} />

          <label style={{ display: "block", marginTop: 14 }}>Reason</label>
          <input className="input" value={form.reason} onChange={e => setForm({ ...form, reason: e.target.value })} />

          <button className="btn btn-secondary" style={{ marginTop: 18, marginInlineEnd: 8 }} onClick={() => {
            setManualSide("");
            setForm(safePayload());
          }}>
            تحميل اختبار آمن NO_TRADE
          </button>

          <button className="btn btn-primary" style={{ marginTop: 18 }} onClick={sendSignal}>
            إرسال NDSP Decision Payload
          </button>
        </div>

        <div className="card">
          <h2>Webhook الحقيقي للربط مع NDSP</h2>

          <p>الرابط:</p>
          <pre style={{ whiteSpace: "pre-wrap" }}>POST https://bot.ndsp.app/api/webhooks/ndsp-signal</pre>

          <p>الهيدر المطلوب:</p>
          <pre style={{ whiteSpace: "pre-wrap" }}>X-NDSP-SECRET: القيمة الموجودة في .env</pre>

          <p>مثال Body آمن لا ينفذ صفقة:</p>
          <pre style={{ whiteSpace: "pre-wrap", direction: "ltr", textAlign: "left" }}>
{JSON.stringify({ user_email: "nawaf@example.com", ...safePayload() }, null, 2)}
          </pre>

          <p style={{ color: "#fbbf24" }}>
            لا تعرض NDSP_WEBHOOK_SECRET داخل الواجهة. يتم حفظه فقط في ملف .env على السيرفر.
          </p>
        </div>

        {message && <div className="card">{message}</div>}

        <p style={{ marginTop: 22 }}>
          <a href="/">{"العودة للوحة التحكم"}</a>
        </p>
      </div>
    </main>
  );
}
