"use client";

import { useEffect, useState } from "react";
import { apiJson, Badge, Card, HunterNav, t, useLang } from "../components/HunterShell";

export default function AccountPage() {
  const { lang, setLang, dir } = useLang();
  const [me, setMe] = useState<any>(null);
  const [settings, setSettings] = useState<any>(null);
  const [liveSafety, setLiveSafety] = useState<any>(null);
  const [risk, setRisk] = useState<any>(null);
  const [message, setMessage] = useState("");
  const [oldPassword, setOldPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");

  async function load() {
    setMessage("");
    try {
      const [meData, settingsData, liveData, riskData] = await Promise.all([
        apiJson("/me"),
        apiJson("/me/settings"),
        apiJson("/live-safety/status"),
        apiJson("/risk/summary")
      ]);

      setMe(meData);
      setSettings(settingsData);
      setLiveSafety(liveData);
      setRisk(riskData);
    } catch (e: any) {
      setMessage(t(lang, "فشل تحميل بيانات الحساب: ", "Failed to load account: ") + e.message);
    }
  }

  async function changePassword() {
    setMessage("");

    if (!oldPassword || !newPassword) {
      setMessage(t(lang, "أدخل كلمة المرور الحالية والجديدة.", "Enter old and new password."));
      return;
    }

    try {
      await apiJson("/me/change-password", {
        method: "POST",
        body: JSON.stringify({
          old_password: oldPassword,
          new_password: newPassword
        })
      });

      setOldPassword("");
      setNewPassword("");
      setMessage(t(lang, "تم تغيير كلمة المرور بنجاح.", "Password changed successfully."));
    } catch (e: any) {
      setMessage(t(lang, "فشل تغيير كلمة المرور: ", "Failed to change password: ") + e.message);
    }
  }

  useEffect(() => {
    load();
  }, []);

  return (
    <main className="container hunter-page" dir={dir}>
      <HunterNav lang={lang} setLang={setLang} />

      <section className="hunter-hero">
        <div>
          <p className="eyebrow">NDSP Account Center</p>
          <h1>{t(lang, "صفحة المستخدم", "User Account")}</h1>
          <p>{t(lang, "إدارة الحساب، المفاتيح، الإعدادات، الأمان، والروابط السريعة.", "Manage account, keys, settings, safety, and quick links.")}</p>
        </div>
        <div className="hunter-watermark">hunter_ksa1</div>
      </section>

      {message && <div className="hunter-alert">{message}</div>}

      <div className="hunter-grid three">
        <Card title={t(lang, "المستخدم", "User")}>
          <p>{me?.email || "-"}</p>
          <Badge ok={me?.is_active}>{me?.is_active ? "Active" : "Disabled"}</Badge>
          {me?.is_admin && <Badge ok>Admin</Badge>}
        </Card>

        <Card title="Binance API">
          <Badge ok={me?.binance_key_configured}>
            {me?.binance_key_configured ? "Configured" : "Missing"}
          </Badge>
          <p>{t(lang, "لا يتم عرض الأسرار أبدًا.", "Secrets are never displayed.")}</p>
        </Card>

        <Card title="Live Safety">
          <Badge ok={liveSafety?.confirmed}>{liveSafety?.confirmed ? "Confirmed" : "Not Confirmed"}</Badge>
          <p><code>{liveSafety?.required_text || "I UNDERSTAND LIVE RISK"}</code></p>
        </Card>
      </div>

      <div className="hunter-grid two">
        <Card title={t(lang, "إعدادات البوت", "Bot Settings")}>
          <div className="kv"><span>Enabled</span><strong>{settings?.enabled ? "Yes" : "No"}</strong></div>
          <div className="kv"><span>Market</span><strong>{settings?.market_type}</strong></div>
          <div className="kv"><span>Symbols</span><strong>{settings?.allowed_symbols}</strong></div>
          <div className="kv"><span>Max Order</span><strong>{settings?.max_order_usdt} USDT</strong></div>
          <div className="kv"><span>Daily Loss</span><strong>{settings?.max_daily_loss_usdt} USDT</strong></div>
          <div className="kv"><span>Max Trades</span><strong>{settings?.max_trades_per_day}</strong></div>
          <div className="kv"><span>Stop Loss</span><strong>{settings?.stop_loss_pct}%</strong></div>
          <div className="kv"><span>Take Profit</span><strong>{settings?.take_profit_pct}%</strong></div>
          <a className="btn btn-primary" href="/">{t(lang, "فتح الإعدادات", "Open Settings")}</a>
        </Card>

        <Card title={t(lang, "ملخص المخاطر", "Risk Summary")}>
          <div className="kv"><span>Bot Enabled</span><strong>{risk?.bot_enabled ? "Yes" : "No"}</strong></div>
          <div className="kv"><span>Daily PnL</span><strong>{risk?.daily_pnl_usdt} USDT</strong></div>
          <div className="kv"><span>Max Daily Loss</span><strong>{risk?.max_daily_loss_usdt} USDT</strong></div>
          <div className="kv"><span>Duplicate Prevention</span><strong>{risk?.prevent_duplicate_positions ? "Yes" : "No"}</strong></div>
          <a className="btn btn-danger" href="/safety">Live Safety</a>
        </Card>
      </div>

      <div className="hunter-grid two">
        <Card title={t(lang, "تغيير كلمة المرور", "Change Password")}>
          <label>{t(lang, "كلمة المرور الحالية", "Old Password")}</label>
          <input className="input" type="password" value={oldPassword} onChange={e => setOldPassword(e.target.value)} />

          <label>{t(lang, "كلمة المرور الجديدة", "New Password")}</label>
          <input className="input" type="password" value={newPassword} onChange={e => setNewPassword(e.target.value)} />

          <button className="btn btn-primary" onClick={changePassword}>
            {t(lang, "تغيير كلمة المرور", "Change Password")}
          </button>
        </Card>

        <Card title={t(lang, "روابط سريعة", "Quick Links")}>
          <div className="quick-links">
            <a className="btn btn-secondary" href="/">Dashboard</a>
            <a className="btn btn-secondary" href="/ndsp">NDSP</a>
            <a className="btn btn-secondary" href="/webhook-config">Webhook</a>
            <a className="btn btn-secondary" href="/logs">Logs</a>
            <a className="btn btn-secondary" href="/risk">Risk</a>
            <a className="btn btn-secondary" href="/admin">Admin</a>
          </div>
        </Card>
      </div>
    </main>
  );
}
