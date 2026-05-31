"use client";

import { useEffect, useState } from "react";
import { apiJson, Badge, Card, HunterNav, t, useLang } from "../components/HunterShell";

export default function AdminPage() {
  const { lang, setLang, dir } = useLang();
  const [me, setMe] = useState<any>(null);
  const [users, setUsers] = useState<any[]>([]);
  const [health, setHealth] = useState<any>(null);
  const [backups, setBackups] = useState<any[]>([]);
  const [logsSummary, setLogsSummary] = useState<any>(null);
  const [trades, setTrades] = useState<any[]>([]);
  const [rejections, setRejections] = useState<any[]>([]);
  const [message, setMessage] = useState("");
  const [cleanupDays, setCleanupDays] = useState(30);
  const [rejectedOnly, setRejectedOnly] = useState(true);

  async function loadAdmin() {
    setMessage("");
    try {
      const meData = await apiJson("/me");
      setMe(meData);

      if (!meData?.is_admin) return;

      const [usersData, healthData, backupsData, summaryData, tradesData, rejectedData] = await Promise.all([
        apiJson("/admin/users"),
        apiJson("/system/health"),
        apiJson("/system/backups"),
        apiJson("/system/logs/summary"),
        apiJson("/system/logs/trades"),
        apiJson("/system/logs/rejections")
      ]);

      setUsers(usersData || []);
      setHealth(healthData);
      setBackups(backupsData?.backups || []);
      setLogsSummary(summaryData);
      setTrades(tradesData || []);
      setRejections(rejectedData || []);
    } catch (e: any) {
      setMessage(t(lang, "فشل تحميل لوحة الإدارة: ", "Failed to load admin: ") + e.message);
    }
  }

  async function patchUser(user: any, patch: any) {
    try {
      await apiJson(`/admin/users/${user.id}`, {
        method: "PATCH",
        body: JSON.stringify(patch)
      });
      await loadAdmin();
    } catch (e: any) {
      setMessage(e.message);
    }
  }

  async function deleteUser(user: any) {
    if (me?.id === user.id) {
      setMessage(t(lang, "لا يمكنك حذف حسابك الحالي.", "You cannot delete your own account."));
      return;
    }

    if (!confirm(t(lang, `تأكيد حذف المستخدم ${user.email}؟`, `Delete user ${user.email}?`))) return;

    try {
      await apiJson(`/admin/users/${user.id}`, { method: "DELETE" });
      await loadAdmin();
    } catch (e: any) {
      setMessage(e.message);
    }
  }

  async function runBackup() {
    if (!confirm(t(lang, "تشغيل نسخة احتياطية الآن؟", "Run backup now?"))) return;

    try {
      const data = await apiJson("/system/backups/run", { method: "POST" });
      setMessage(t(lang, "تم تشغيل النسخة الاحتياطية: ", "Backup completed: ") + (data?.stdout || data?.status || ""));
      await loadAdmin();
    } catch (e: any) {
      setMessage(e.message);
    }
  }

  async function cleanupLogs() {
    if (!confirm(t(lang, "تأكيد تنظيف السجلات؟", "Confirm logs cleanup?"))) return;

    try {
      await apiJson("/system/logs/cleanup", {
        method: "POST",
        body: JSON.stringify({
          older_than_days: cleanupDays,
          rejected_only: rejectedOnly
        })
      });
      setMessage(t(lang, "تم تنظيف السجلات.", "Logs cleaned."));
      await loadAdmin();
    } catch (e: any) {
      setMessage(t(lang, "قد لا يكون endpoint التنظيف متاحًا: ", "Cleanup endpoint may not be available: ") + e.message);
    }
  }

  useEffect(() => {
    loadAdmin();
  }, []);

  if (me && !me.is_admin) {
    return (
      <main className="container hunter-page" dir={dir}>
        <HunterNav lang={lang} setLang={setLang} />
        <Card title={t(lang, "الإدارة", "Admin")}>
          <p>{t(lang, "هذه الصفحة مخصصة للمشرف فقط.", "This page is for admins only.")}</p>
        </Card>
      </main>
    );
  }

  return (
    <main className="container hunter-page" dir={dir}>
      <HunterNav lang={lang} setLang={setLang} />

      <section className="hunter-hero admin">
        <div>
          <p className="eyebrow">Admin Command Center</p>
          <h1>{t(lang, "لوحة الإدارة", "Admin Panel")}</h1>
          <p>{t(lang, "إدارة المستخدمين، النظام، النسخ الاحتياطية، والسجلات.", "Users, system health, backups, and logs.")}</p>
        </div>
        <div className="hunter-watermark">hunter_ksa1</div>
      </section>

      {message && <div className="hunter-alert">{message}</div>}

      <div className="hunter-grid three">
        <Card title={t(lang, "المستخدمون", "Users")}>
          <strong>{users.length}</strong>
          <p>Active: {users.filter(x => x.is_active).length}</p>
          <p>Admins: {users.filter(x => x.is_admin).length}</p>
        </Card>

        <Card title={t(lang, "النظام", "System")}>
          <div className="kv"><span>API</span><strong>{health?.api || "-"}</strong></div>
          <div className="kv"><span>DB</span><strong>{health?.database || "-"}</strong></div>
          <div className="kv"><span>Docker</span><strong>{health?.docker_status || "-"}</strong></div>
        </Card>

        <Card title={t(lang, "وضع Binance", "Binance Mode")}>
          <Badge ok={health?.binance_mode !== "live"}>{health?.binance_mode || "-"}</Badge>
          {health?.binance_mode === "live" && <p className="warning-text">LIVE RISK</p>}
        </Card>
      </div>

      <Card title={t(lang, "إدارة المستخدمين", "User Management")}>
        <div className="table-wrap">
          <table className="hunter-table">
            <thead>
              <tr>
                <th>ID</th><th>Email</th><th>Active</th><th>Admin</th><th>Binance</th><th>Settings</th><th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {users.map(user => (
                <tr key={user.id}>
                  <td>{user.id}</td>
                  <td>{user.email}</td>
                  <td><Badge ok={user.is_active}>{user.is_active ? "Active" : "Disabled"}</Badge></td>
                  <td><Badge ok={user.is_admin}>{user.is_admin ? "Admin" : "User"}</Badge></td>
                  <td>{user.binance_key_configured ? "Yes" : "No"}</td>
                  <td>{user.settings_configured ? "Yes" : "No"}</td>
                  <td className="actions">
                    <button className="btn btn-secondary" onClick={() => patchUser(user, { is_active: !user.is_active })}>
                      {user.is_active ? "Disable" : "Activate"}
                    </button>
                    <button className="btn btn-secondary" onClick={() => patchUser(user, { is_admin: !user.is_admin })}>
                      {user.is_admin ? "Remove Admin" : "Make Admin"}
                    </button>
                    <button className="btn btn-danger" onClick={() => deleteUser(user)}>Delete</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      <div className="hunter-grid two">
        <Card title={t(lang, "النسخ الاحتياطية", "Backups")}>
          <button className="btn btn-primary" onClick={runBackup}>Run Backup Now</button>
          <div className="table-wrap">
            <table className="hunter-table">
              <thead><tr><th>Name</th><th>Size</th><th>Modified</th></tr></thead>
              <tbody>
                {backups.map((b, i) => (
                  <tr key={i}>
                    <td>{b.name}</td>
                    <td>{b.size_bytes}</td>
                    <td>{String(b.modified_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>

        <Card title={t(lang, "ملخص السجلات", "Logs Summary")}>
          <div className="kv"><span>Total</span><strong>{logsSummary?.total}</strong></div>
          <div className="kv"><span>Closed</span><strong>{logsSummary?.closed}</strong></div>
          <div className="kv"><span>Simulated</span><strong>{logsSummary?.simulated}</strong></div>
          <div className="kv"><span>Rejected/Failed</span><strong>{logsSummary?.rejected_or_failed}</strong></div>
          <a className="btn btn-secondary" href="/system/logs/export.csv">Export CSV</a>
        </Card>
      </div>

      <Card title={t(lang, "تنظيف السجلات", "Cleanup Logs")}>
        <label>Older Than Days</label>
        <input className="input" type="number" value={cleanupDays} onChange={e => setCleanupDays(Number(e.target.value))} />
        <label>
          <input type="checkbox" checked={rejectedOnly} onChange={e => setRejectedOnly(e.target.checked)} /> Rejected Only
        </label>
        <button className="btn btn-danger" onClick={cleanupLogs}>Cleanup</button>
      </Card>

      <Card title={t(lang, "آخر الصفقات", "Recent Trades")}>
        <div className="table-wrap">
          <table className="hunter-table">
            <thead><tr><th>ID</th><th>Symbol</th><th>Side</th><th>Notional</th><th>Status</th><th>Mode</th><th>Reason</th></tr></thead>
            <tbody>
              {trades.slice(0, 40).map(x => (
                <tr key={x.id}>
                  <td>{x.id}</td><td>{x.symbol}</td><td>{x.side}</td><td>{x.notional_usdt}</td><td>{x.status}</td><td>{x.mode}</td><td>{x.reason}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      <Card title={t(lang, "الصفقات المرفوضة", "Rejected Trades")}>
        <div className="table-wrap">
          <table className="hunter-table">
            <thead><tr><th>ID</th><th>Symbol</th><th>Side</th><th>Status</th><th>Reason</th><th>Exchange</th></tr></thead>
            <tbody>
              {rejections.slice(0, 40).map(x => (
                <tr key={x.id}>
                  <td>{x.id}</td><td>{x.symbol}</td><td>{x.side}</td><td>{x.status}</td><td>{x.reason}</td><td>{String(x.exchange_response || "")}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </main>
  );
}
