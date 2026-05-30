"use client";

import { useEffect, useState } from "react";
import { api, setToken, clearToken, getToken } from "../lib/api";

type User = {
  id: number;
  email: string;
  is_active: boolean;
  binance_key_configured: boolean;
  settings_configured: boolean;
};

export default function HomePage() {
const [tokenReady, setTokenReady] = useState(false);
  const [tab, setTab] = useState("dashboard");
  const [email, setEmail] = useState("nawaf@example.com");
  const [password, setPassword] = useState("");
  const [authMode, setAuthMode] = useState<"login" | "register">("login");
  const [registerEmail, setRegisterEmail] = useState("");
  const [registerPassword, setRegisterPassword] = useState("");
  const [registerInviteCode, setRegisterInviteCode] = useState("");
  const [me, setMe] = useState<User | null>(null);
  const [settings, setSettings] = useState<any>(null);
  const [trades, setTrades] = useState<any[]>([]);
  const [message, setMessage] = useState("");
  const [binanceKey, setBinanceKey] = useState("");
  const [binanceSecret, setBinanceSecret] = useState("");

  const [settingsForm, setSettingsForm] = useState({
    enabled: true,
    allowed_symbols: "BTC/USDT,ETH/USDT",
    max_order_usdt: 10,
    max_daily_loss_usdt: 20,
    max_trades_per_day: 3,
    stop_loss_pct: 0,
    take_profit_pct: 0,
    prevent_duplicate_positions: true,
    telegram_enabled: true,
    email_enabled: true
  });

  const [signalForm, setSignalForm] = useState({
    symbol: "BTC/USDT",
    side: "BUY",
    notional_usdt: 10,
    reason: "dashboard manual test signal"
  });

  useEffect(() => {
    setTokenReady(true);
    if (getToken()) {
      loadAll();
    }
  }, []);

  async function registerUser() {
    setMessage("");
    try {
      const res = await fetch("/api/auth/register", {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          email: registerEmail,
          password: registerPassword,
          invite_code: registerInviteCode || null
        })
      });

      const data = await res.json();

      if (!res.ok) {
        throw new Error(JSON.stringify(data));
      }

      setToken(data.access_token);
      setMessage("تم إنشاء الحساب وتسجيل الدخول بنجاح");
      await loadAll();
    } catch (e: any) {
      setMessage("فشل إنشاء الحساب: " + e.message);
    }
  }

  async function login() {
    setMessage("");
    try {
      const body = new URLSearchParams();
      body.append("username", email);
      body.append("password", password);

      const res = await fetch("/api/auth/login", {
        method: "POST",
        headers: {
          "Content-Type": "application/x-www-form-urlencoded"
        },
        body
      });

      const data = await res.json();

      if (!res.ok) {
        throw new Error(JSON.stringify(data));
      }

      setToken(data.access_token);
      setMessage("تم تسجيل الدخول بنجاح");
      await loadAll();
    } catch (e: any) {
      setMessage("فشل تسجيل الدخول: " + e.message);
    }
  }

  async function loadAll() {
    try {
      const meData = await api("/me");
      setMe(meData);

      const settingsData = await api("/me/settings");
      setSettings(settingsData);
      if (settingsData) {
        setSettingsForm(settingsData);
      }

      const tradesData = await api("/trades");
      setTrades(tradesData);
    } catch (e: any) {
      setMessage("خطأ في تحميل البيانات: " + e.message);
    }
  }

  async function saveSettings() {
    setMessage("");
    try {
      const data = await api("/me/settings", {
        method: "POST",
        body: JSON.stringify(settingsForm)
      });
      setSettings(data.settings);
      setMessage("تم حفظ الإعدادات");
      await loadAll();
    } catch (e: any) {
      setMessage("فشل حفظ الإعدادات: " + e.message);
    }
  }

  async function saveBinanceKey() {
    setMessage("");
    try {
      await api("/me/binance-key", {
        method: "POST",
        body: JSON.stringify({
          api_key: binanceKey,
          api_secret: binanceSecret
        })
      });
      setBinanceKey("");
      setBinanceSecret("");
      setMessage("تم حفظ مفاتيح Binance بشكل مشفر");
      await loadAll();
    } catch (e: any) {
      setMessage("فشل حفظ المفاتيح: " + e.message);
    }
  }

  async function testAlert() {
    setMessage("");
    try {
      const data = await api("/bot/test-alert", { method: "POST" });
      setMessage(`Telegram: ${data.telegram_sent} | Email: ${data.email_sent}`);
    } catch (e: any) {
      setMessage("فشل اختبار التنبيهات: " + e.message);
    }
  }

  async function testSignal() {
    setMessage("");
    try {
      const data = await api("/bot/test-signal", {
        method: "POST",
        body: JSON.stringify(signalForm)
      });
      setMessage(`تم تنفيذ الإشارة. Status: ${data.status} | Mode: ${data.mode}`);
      await loadAll();
    } catch (e: any) {
      setMessage("فشل تنفيذ الإشارة: " + e.message);
    }
  }

  async function emergencyStop() {
    setMessage("");
    try {
      await api("/emergency-stop", { method: "POST" });
      setMessage("تم إيقاف البوت فورًا");
      await loadAll();
    } catch (e: any) {
      setMessage("فشل الإيقاف: " + e.message);
    }
  }

  function logout() {
    clearToken();
    setMe(null);
    setSettings(null);
    setTrades([]);
    setMessage("تم تسجيل الخروج");
  }

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
          <h2>{"آخر صفقة"}</h2>
          <p style={{ color: "#94a3b8" }}>{"لا توجد صفقات حتى الآن"}</p>
        </div>
      );
    }

    const isBuy = trade.side === "BUY";
    const isClosed = trade.status === "closed";

    return (
      <div className="card last-trade-card">
        <div className="last-trade-header">
          <div>
            <h2 style={{ margin: 0 }}>{"آخر صفقة"}</h2>
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
            <span>{"زوج التداول"}</span>
            <strong>{trade.symbol}</strong>
          </div>

          <div className="trade-main-value">
            <span>{"القيمة USDT"}</span>
            <strong>{trade.notional_usdt} USDT</strong>
          </div>
        </div>

        <div className="trade-details-grid">
          <div className="trade-detail-item">
            <span>{"الكمية"}</span>
            <strong>{trade.amount}</strong>
          </div>

          <div className="trade-detail-item">
            <span>{"السعر"}</span>
            <strong>{trade.price}</strong>
          </div>

          <div className="trade-detail-item">
            <span>{"وقت الإنشاء"}</span>
            <strong>{formatDate(trade.created_at)}</strong>
          </div>

          <div className="trade-detail-item">
            <span>{"الوضع"}</span>
            <strong>{trade.mode}</strong>
          </div>

          <div className="trade-detail-item">
            <span>Stop Loss Preview</span>
            <strong>{trade.stop_loss_price || 0}</strong>
          </div>

          <div className="trade-detail-item">
            <span>Take Profit Preview</span>
            <strong>{trade.take_profit_price || 0}</strong>
          </div>

          <div className="trade-detail-item">
            <span>Protective Status</span>
            <strong>{trade.protective_orders_status || "preview"}</strong>
          </div>
        </div>

        <div className="trade-reason">
          <span>{"السبب"}</span>
          <p>{trade.reason || "—"}</p>
        </div>
      </div>
    );
  }

  if (!tokenReady) return null;

  if (!getToken() || !me) {
    return (
      <main className="container auth-page">

      <div className="center-signature-badge">
        <span className="center-signature-badge__label">Signature</span>
        <span className="center-signature-badge__value">hunter_ksa1</span>
      </div>

        <div className="hunter-bg-signature">
          <div className="hunter-mark">hunter_ksa1</div>
          <div className="hunter-layers">16 LAYERS POWER ENGINE</div>
        </div>

        <div className="auth-card">
          <div className="auth-glow" />

          <div className="auth-brand">
            <div className="brand-kicker">NDSP • Binance • Execution Bot</div>
            <h1>NDSP Trading Bot</h1>
            <p>لوحة تحكم احترافية لإدارة البوت، التنبيهات، الصفقات، ومفاتيح Binance.</p>
          </div>

          <div className="auth-switch">
            <button
              className={authMode === "login" ? "active" : ""}
              onClick={() => setAuthMode("login")}
            >
              تسجيل الدخول
            </button>
            <button
              className={authMode === "register" ? "active" : ""}
              onClick={() => setAuthMode("register")}
            >
              حساب جديد
            </button>
          </div>

          {authMode === "login" ? (
            <div className="auth-form">
              <label>{"البريد الإلكتروني"}</label>
              <input
                className="input"
                value={email}
                onChange={e => setEmail(e.target.value)}
                placeholder="nawaf@example.com"
              />

              <label style={{ marginTop: 12, display: "block" }}>{"كلمة المرور"}</label>
              <input
                className="input"
                type="password"
                value={password}
                onChange={e => setPassword(e.target.value)}
                placeholder="••••••••"
              />

              <button className="btn btn-primary auth-main-btn" onClick={login}>
                دخول
              </button>
            </div>
          ) : (
            <div className="auth-form">
              <label>إيميل الحساب الجديد</label>
              <input
                className="input"
                value={registerEmail}
                onChange={e => setRegisterEmail(e.target.value)}
                placeholder="friend@example.com"
              />

              <label style={{ marginTop: 12, display: "block" }}>{"كلمة المرور"}</label>
              <input
                className="input"
                type="password"
                value={registerPassword}
                onChange={e => setRegisterPassword(e.target.value)}
                placeholder="8 أحرف على الأقل"
              />

              <label style={{ marginTop: 12, display: "block" }}>{"كود الدعوة"}</label>
              <input
                className="input"
                value={registerInviteCode}
                onChange={e => setRegisterInviteCode(e.target.value)}
                placeholder="Invite Code"
              />

              <button className="btn btn-primary auth-main-btn" onClick={registerUser}>
                إنشاء حساب
              </button>
            </div>
          )}

          {message && <p className="auth-message">{message}</p>}

          <div className="auth-warning">
            لا تستخدم مفاتيح Binance Live قبل تفعيل إدارة المخاطر الكاملة.
          </div>
        </div>
      </main>
    );
  }

  return (
    <main className="container">
      <div className="card">
        <div style={{ display: "flex", justifyContent: "space-between", gap: 12, alignItems: "center", flexWrap: "wrap" }}>
          <div>
            <h1 style={{ margin: 0 }}>NDSP Trading Bot</h1>
            <p style={{ marginBottom: 0 }}>مرحبًا، {me.email}</p>
          </div>
          <button className="btn btn-secondary" onClick={logout}>{"تسجيل الخروج"}</button>
        </div>
      </div>

      <div className="nav">
        {[
          ["dashboard", "الرئيسية"],
          ["settings", "الإعدادات"],
          ["binance", "Binance API"],
          ["signal", "اختبار صفقة"],
          ["trades", "الصفقات"],
          ["alerts", "التنبيهات"],
          ["risk", "إيقاف طارئ"],
          ["links", "روابط متقدمة"]
        ].map(([id, label]) => (
          <button key={id} className={tab === id ? "active" : ""} onClick={() => setTab(id)}>
            {label}
          </button>
        ))}
      </div>

      {message && (
        <div className="card">
          <strong>{message}</strong>
        </div>
      )}

      {tab === "dashboard" && (
        <>
          <div className="grid grid-3">
            <div className="card">
              <h3>{"حالة البوت"}</h3>
              <span className={`badge ${settings?.enabled ? "badge-green" : "badge-red"}`}>
                {settings?.enabled ? "Enabled" : "Disabled"}
              </span>
            </div>

            <div className="card">
              <h3>Binance API</h3>
              <span className={`badge ${me.binance_key_configured ? "badge-green" : "badge-red"}`}>
                {me.binance_key_configured ? "Configured" : "Missing"}
              </span>
            </div>

            <div className="card">
              <h3>{"عدد الصفقات"}</h3>
              <strong style={{ fontSize: 32 }}>{trades.length}</strong>
            </div>
          </div>

          <LastTradeCard trade={trades[0]} />
        </>
      )}

      {tab === "settings" && (
        <div className="card">
          <h2>{"إعدادات البوت"}</h2>

          <label>
            <input
              type="checkbox"
              checked={settingsForm.enabled}
              onChange={e => setSettingsForm({ ...settingsForm, enabled: e.target.checked })}
            />{" "}
            تشغيل البوت
          </label>

          <label style={{ display: "block", marginTop: 14 }}>{"الأزواج المسموحة"}</label>
          <input className="input" value={settingsForm.allowed_symbols} onChange={e => setSettingsForm({ ...settingsForm, allowed_symbols: e.target.value })} />

          <div className="grid grid-3" style={{ marginTop: 14 }}>
            <div>
              <label>أقصى قيمة للصفقة USDT</label>
              <input className="input" type="number" value={settingsForm.max_order_usdt} onChange={e => setSettingsForm({ ...settingsForm, max_order_usdt: Number(e.target.value) })} />
            </div>
            <div>
              <label>أقصى خسارة يومية USDT</label>
              <input className="input" type="number" value={settingsForm.max_daily_loss_usdt} onChange={e => setSettingsForm({ ...settingsForm, max_daily_loss_usdt: Number(e.target.value) })} />
            </div>
            <div>
              <label>أقصى عدد صفقات يوميًا</label>
              <input className="input" type="number" value={settingsForm.max_trades_per_day} onChange={e => setSettingsForm({ ...settingsForm, max_trades_per_day: Number(e.target.value) })} />
            </div>
          </div>

          <div className="risk-settings-panel">
            <h3>{"إدارة المخاطر"}</h3>

            <div className="grid grid-3">
              <div>
                <label>Stop Loss %</label>
                <input
                  className="input"
                  type="number"
                  value={settingsForm.stop_loss_pct || 0}
                  onChange={e => setSettingsForm({ ...settingsForm, stop_loss_pct: Number(e.target.value) })}
                />
              </div>

              <div>
                <label>Take Profit %</label>
                <input
                  className="input"
                  type="number"
                  value={settingsForm.take_profit_pct || 0}
                  onChange={e => setSettingsForm({ ...settingsForm, take_profit_pct: Number(e.target.value) })}
                />
              </div>

              <div>
                <label>منع تكرار الصفقة</label>
                <div className="toggle-box">
                  <input
                    type="checkbox"
                    checked={settingsForm.prevent_duplicate_positions ?? true}
                    onChange={e => setSettingsForm({ ...settingsForm, prevent_duplicate_positions: e.target.checked })}
                  />
                  <span>منع نفس الزوج والاتجاه في نفس اليوم</span>
                </div>
              </div>
            </div>

            <p className="risk-note">
              Stop Loss و Take Profit محفوظة الآن كإعدادات مخاطرة. تنفيذ أوامر حماية فعلية على Binance سيتم في مرحلة OCO/Protective Orders.
            </p>
          </div>

          <div style={{ marginTop: 14 }}>
            <label>
              <input type="checkbox" checked={settingsForm.telegram_enabled} onChange={e => setSettingsForm({ ...settingsForm, telegram_enabled: e.target.checked })} /> Telegram
            </label>
            <br />
            <label>
              <input type="checkbox" checked={settingsForm.email_enabled} onChange={e => setSettingsForm({ ...settingsForm, email_enabled: e.target.checked })} /> Email
            </label>
          </div>

          <button className="btn btn-primary" style={{ marginTop: 18 }} onClick={saveSettings}>
            حفظ الإعدادات
          </button>
        </div>
      )}

      {tab === "binance" && (
        <div className="card">
          <h2>Binance API</h2>
          <p style={{ color: "#fbbf24" }}>
            استخدم Testnet الآن. لا تستخدم Live قبل إضافة Stop Loss / Take Profit.
          </p>

          <label>API Key</label>
          <input className="input" value={binanceKey} onChange={e => setBinanceKey(e.target.value)} />

          <label style={{ marginTop: 14, display: "block" }}>API Secret</label>
          <input className="input" type="password" value={binanceSecret} onChange={e => setBinanceSecret(e.target.value)} />

          <button className="btn btn-primary" style={{ marginTop: 18 }} onClick={saveBinanceKey}>
            حفظ المفاتيح
          </button>
        </div>
      )}

      {tab === "signal" && (
        <div className="card">
          <h2>اختبار صفقة Testnet</h2>

          <label>Symbol</label>
          <input className="input" value={signalForm.symbol} onChange={e => setSignalForm({ ...signalForm, symbol: e.target.value })} />

          <label style={{ marginTop: 14, display: "block" }}>Side</label>
          <select className="input" value={signalForm.side} onChange={e => setSignalForm({ ...signalForm, side: e.target.value })}>
            <option value="BUY">BUY</option>
            <option value="SELL">SELL</option>
          </select>

          <label style={{ marginTop: 14, display: "block" }}>Notional USDT</label>
          <input className="input" type="number" value={signalForm.notional_usdt} onChange={e => setSignalForm({ ...signalForm, notional_usdt: Number(e.target.value) })} />

          <label style={{ marginTop: 14, display: "block" }}>Reason</label>
          <input className="input" value={signalForm.reason} onChange={e => setSignalForm({ ...signalForm, reason: e.target.value })} />

          <button className="btn btn-primary" style={{ marginTop: 18 }} onClick={testSignal}>
            تنفيذ اختبار
          </button>
        </div>
      )}

      {tab === "trades" && (
        <div className="card">
          <h2>سجل الصفقات</h2>
          <button className="btn btn-secondary" onClick={loadAll}>{"تحديث"}</button>
          <div style={{ overflowX: "auto", marginTop: 14 }}>
            <table className="table">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Symbol</th>
                  <th>Side</th>
                  <th>Amount</th>
                  <th>Price</th>
                  <th>USDT</th>
                  <th>SL</th>
                  <th>TP</th>
                  <th>Protective</th>
                  <th>Status</th>
                  <th>Mode</th>
                  <th>Time</th>
                </tr>
              </thead>
              <tbody>
                {trades.map(t => (
                  <tr key={t.id}>
                    <td>{t.id}</td>
                    <td>{t.symbol}</td>
                    <td>{t.side}</td>
                    <td>{t.amount}</td>
                    <td>{t.price}</td>
                    <td>{t.notional_usdt}</td>
                    <td>{t.stop_loss_price || 0}</td>
                    <td>{t.take_profit_price || 0}</td>
                    <td>{t.protective_orders_status || "preview"}</td>
                    <td>{t.status}</td>
                    <td>{t.mode}</td>
                    <td>{t.created_at}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {tab === "alerts" && (
        <div className="card">
          <h2>اختبار التنبيهات</h2>
          <button className="btn btn-primary" onClick={testAlert}>اختبار Telegram و Email</button>
        </div>
      )}


      {tab === "links" && (
        <div className="card">
          <h2>{"روابط متقدمة"}</h2>
          <div className="grid grid-2">
            <a className="btn btn-secondary" href="/admin">صفحة Admin لإدارة الأصدقاء</a>
            <a className="btn btn-secondary" href="/account">تغيير كلمة المرور</a>
            <a className="btn btn-secondary" href="/risk">Risk Center / Daily PnL</a>
            <a className="btn btn-secondary" href="/safety">Live Safety</a>
            <a className="btn btn-secondary" href="/ndsp">NDSP Signal Bridge</a>
            <a className="btn btn-secondary" href="/webhook-config">Webhook Config</a>
            <a className="btn btn-secondary" href="/logs">{"مركز السجلات"}</a>
            <a className="btn btn-secondary" href="/health">Health Monitor</a>
            <a className="btn btn-secondary" href="/backups">Backup Center</a>
            <a className="btn btn-secondary" href="/docs">Swagger API</a>
          </div>
        </div>
      )}

      {tab === "risk" && (
        <div className="card">
          <h2>Emergency Stop</h2>
          <p style={{ color: "#fecaca" }}>هذا الزر يوقف البوت فورًا للمستخدم الحالي.</p>
          <button className="btn btn-danger" onClick={emergencyStop}>{"إيقاف طارئ"}</button>
        </div>
      )}
    </main>
  );
}
