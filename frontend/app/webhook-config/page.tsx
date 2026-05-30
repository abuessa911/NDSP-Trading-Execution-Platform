"use client";

import { useEffect, useState } from "react";
import { api } from "../../lib/api";

export default function WebhookConfigPage() {
const [config, setConfig] = useState<any>(null);
  const [newSecret, setNewSecret] = useState("");
  const [message, setMessage] = useState("");
  const [marketType, setMarketType] = useState("spot");
  const [availableSymbols, setAvailableSymbols] = useState<string[]>([]);
  const [symbolsLoading, setSymbolsLoading] = useState(false);
  const [testBody, setTestBody] = useState<any>({
    user_email: "nawaf@example.com",
    symbol: "ETH/USDT",
    side: "BUY",
    notional_usdt: 10,
    reason: "NDSP webhook config page test",
    ndsp_layer: "layer-1",
    signal_id: "webhook-config-test"
  });

  async function loadSymbols(selectedMarket = "spot") {
    setSymbolsLoading(true);
    try {
      const data = await api(`/symbols/${selectedMarket}`);
      const symbols = Array.isArray(data?.symbols) ? data.symbols : [];
      setAvailableSymbols(symbols);

      if (symbols.length) {
        setTestBody(prev => ({
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

  async function loadConfig() {
    setMessage("");
    try {
      const data = await api("/ndsp/webhook-config");
      setConfig(data);
      setTestBody(data.example_body || testBody);
    } catch (e: any) {
      setMessage(`${"فشل تحميل إعدادات Webhook"}: ` + e.message);
    }
  }

  async function rotateSecret() {
    setMessage("");

    const ok = window.confirm(
      "توليد Secret جديد سيجعل أي Secret قديم غير صالح. هل تريد المتابعة؟"
    );

    if (!ok) return;

    try {
      const data = await api("/ndsp/webhook-config/rotate", {
        method: "POST"
      });

      setNewSecret(data.new_secret);
      setMessage("تم توليد Secret جديد. انسخه الآن واحفظه في منظومة NDSP.");
      await loadConfig();
    } catch (e: any) {
      setMessage(`${"فشل توليد Secret جديد"}: ` + e.message);
    }
  }

  async function testWebhook() {
    setMessage("");

    if (!newSecret) {
      setMessage("للاختبار من هذه الصفحة، ولّد Secret جديد أو استخدم curl من السيرفر بالسكرت الموجود في .env.");
      return;
    }

    try {
      const res = await fetch("/api/webhooks/ndsp-signal", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-NDSP-SECRET": newSecret
        },
        body: JSON.stringify({
          ...testBody,
          signal_id: "webhook-config-test-" + Date.now()
        })
      });

      const data = await res.json();

      if (!res.ok) {
        throw new Error(JSON.stringify(data));
      }

      setMessage("تم اختبار Webhook بنجاح: " + JSON.stringify(data));
    } catch (e: any) {
      setMessage(`${"فشل اختبار Webhook"}: ` + e.message);
    }
  }

  useEffect(() => {
    loadConfig();
    loadSymbols("spot");
  }, []);

  return (
    <main className="container">
      <div className="card webhook-config-card">
        <h1>{"إعدادات NDSP Webhook"}</h1>
        <p>
          من هنا يتم ربط منظومة NDSP الحقيقية مع بوت التنفيذ عبر Webhook آمن.
        </p>

        {message && <div className="card">{message}</div>}

        {config && (
          <>
            <div className="webhook-grid">
              <div className="webhook-box">
                <span>Webhook URL</span>
                <strong>{config.webhook_url}</strong>
              </div>

              <div className="webhook-box">
                <span>Method</span>
                <strong>{config.method}</strong>
              </div>

              <div className="webhook-box">
                <span>Header</span>
                <strong>{config.header_name}</strong>
              </div>

              <div className="webhook-box">
                <span>Secret Configured</span>
                <strong>{config.configured ? "Yes" : "No"}</strong>
              </div>

              <div className="webhook-box">
                <span>Secret Length</span>
                <strong>{config.secret_length}</strong>
              </div>

              <div className="webhook-box">
                <span>Duplicate Secrets</span>
                <strong>{config.duplicate_count}</strong>
              </div>
            </div>

            <div className="card">
              <h2>Example Body</h2>
              <pre className="webhook-pre">
{JSON.stringify(config.example_body, null, 2)}
              </pre>
            </div>

            <div className="card">
              <h2>{"توليد Secret جديد"}</h2>
              <p style={{ color: "#fbbf24" }}>
                بعد التوليد، انسخ Secret فورًا وضعه في منظومة NDSP. لن يتم عرضه مرة أخرى.
              </p>

              <button className="btn btn-danger" onClick={rotateSecret}>
                توليد Secret جديد
              </button>

              {newSecret && (
                <div className="new-secret-box">
                  <span>{"Secret الجديد"}</span>
                  <code>{newSecret}</code>
                </div>
              )}
            </div>

            <div className="card">
              <h2>{"اختبار Webhook من الصفحة"}</h2>

              <label>User Email</label>
              <input
                className="input"
                value={testBody.user_email}
                onChange={e => setTestBody({ ...testBody, user_email: e.target.value })}
              />

              <label style={{ display: "block", marginTop: 12 }}>نوع السوق</label>
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

              <label style={{ display: "block", marginTop: 12 }}>العملة</label>
              <select
                className="input technical-input"
                value={testBody.symbol}
                onChange={e => setTestBody({ ...testBody, symbol: e.target.value })}
              >
                {symbolsLoading && <option value={testBody.symbol}>جاري تحميل العملات...</option>}
                {!symbolsLoading && availableSymbols.length === 0 && <option value={testBody.symbol}>{testBody.symbol}</option>}
                {availableSymbols.map(symbol => (
                  <option key={symbol} value={symbol}>{symbol}</option>
                ))}
              </select>

              <label style={{ display: "block", marginTop: 12 }}>Side</label>
              <select
                className="input"
                value={testBody.side}
                onChange={e => setTestBody({ ...testBody, side: e.target.value })}
              >
                <option value="BUY">BUY</option>
                <option value="SELL">SELL</option>
              </select>

              <label style={{ display: "block", marginTop: 12 }}>Notional USDT</label>
              <input
                className="input"
                type="number"
                value={testBody.notional_usdt}
                onChange={e => setTestBody({ ...testBody, notional_usdt: Number(e.target.value) })}
              />

              <label style={{ display: "block", marginTop: 12 }}>NDSP Layer</label>
              <input
                className="input"
                value={testBody.ndsp_layer}
                onChange={e => setTestBody({ ...testBody, ndsp_layer: e.target.value })}
              />

              <label style={{ display: "block", marginTop: 12 }}>Reason</label>
              <input
                className="input"
                value={testBody.reason}
                onChange={e => setTestBody({ ...testBody, reason: e.target.value })}
              />

              <button className="btn btn-primary" style={{ marginTop: 18 }} onClick={testWebhook}>
                اختبار Webhook
              </button>
            </div>
          </>
        )}

        <p style={{ marginTop: 22 }}>
          <a href="/">{"العودة للوحة التحكم"}</a>
        </p>
      </div>
    </main>
  );
}
