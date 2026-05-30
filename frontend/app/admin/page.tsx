"use client";

import { useEffect, useState } from "react";

// --- Inlined API helper (was ../../lib/api) ---
const API_BASE = "/api"; // nginx proxies /api/* to backend

async function api(path: string, options: RequestInit = {}) {
  const res = await fetch(API_BASE + path, {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {})
    },
    credentials: "include",
    ...options
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail || body.message || detail;
    } catch {
      /* ignore non-JSON error bodies */
    }
    throw new Error(detail);
  }
  if (res.status === 204) return null;
  return res.json();
}

export default function AdminPage() {
const [users, setUsers] = useState<any[]>([]);
  const [message, setMessage] = useState("");

  async function loadUsers() {
    setMessage("");
    try {
      const data = await api("/admin/users");
      setUsers(data || []);
    } catch (e: any) {
      setMessage("فشل تحميل المستخدمين" + ": " + e.message);
    }
  }

  async function updateUser(id: number, patch: any) {
    setMessage("");
    try {
      await api(`/admin/users/${id}`, {
        method: "PATCH",
        body: JSON.stringify(patch)
      });
      setMessage("تم تحديث المستخدم");
      await loadUsers();
    } catch (e: any) {
      setMessage("فشل التحديث" + ": " + e.message);
    }
  }

  async function deleteUser(id: number, email: string) {
    setMessage("");
    const ok = window.confirm(`${"هل تريد حذف هذا المستخدم نهائياً؟"}\n${email}`);
    if (!ok) return;
    try {
      await api(`/admin/users/${id}`, { method: "DELETE" });
      setMessage("تم حذف المستخدم");
      await loadUsers();
    } catch (e: any) {
      setMessage("فشل الحذف" + ": " + e.message);
    }
  }

  useEffect(() => {
    loadUsers();
  }, []);

  return (
    <main className="container">
      <div className="card">
        <h1>{"إدارة المستخدمين"}</h1>
        <p style={{ color: "#94a3b8", marginBottom: 18 }}>
          {"إدارة حسابات المستخدمين والصلاحيات والوصول."}
        </p>

        {message && (
          <div className="card" style={{ color: "#bfdbfe" }}>
            {message}
          </div>
        )}

        <button className="btn btn-secondary" onClick={loadUsers}>
          {"تحديث القائمة"}
        </button>

        <div style={{ display: "grid", gap: 14, marginTop: 22 }}>
          {users.map(u => (
            <div className="card" key={u.id}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 12, flexWrap: "wrap" }}>
                <div>
                  <div style={{ fontSize: 12, color: "#64748b" }}>ID #{u.id}</div>
                  <div style={{ fontWeight: 800 }}>{u.email}</div>
                </div>

                <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
                  <span className={u.is_active ? "badge badge-green" : "badge badge-red"}>
                    {u.is_active ? "Active" : "Disabled"}
                  </span>
                  <span className={u.is_admin ? "badge badge-green" : "badge"}>
                    {u.is_admin ? "Admin" : "User"}
                  </span>
                  <span className={u.binance_key_configured ? "badge badge-green" : "badge badge-red"}>
                    {u.binance_key_configured ? "Binance OK" : "No Binance"}
                  </span>
                </div>
              </div>

              <div style={{ display: "flex", gap: 10, flexWrap: "wrap", marginTop: 16 }}>
                <button
                  className={u.is_active ? "btn btn-danger" : "btn"}
                  onClick={() => updateUser(u.id, { is_active: !u.is_active })}
                >
                  {u.is_active ? "تعطيل" : "تفعيل"}
                </button>

                <button
                  className="btn btn-secondary"
                  onClick={() => updateUser(u.id, { is_admin: !u.is_admin })}
                >
                  {u.is_admin ? "إزالة المدير" : "تعيين مدير"}
                </button>

                <button
                  className="btn btn-danger"
                  onClick={() => deleteUser(u.id, u.email)}
                >
                  {"حذف"}
                </button>
              </div>
            </div>
          ))}
        </div>

        <p style={{ marginTop: 24 }}>
          <a href="/">{"العودة للوحة التحكم"}</a>
        </p>
      </div>
    </main>
  );
}
