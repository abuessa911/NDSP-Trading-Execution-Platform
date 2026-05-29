#!/usr/bin/env bash
set -e

cd /home/nawaf511/ndsp-binance-bot

STAMP="$(date +%Y%m%d_%H%M%S)"
BACKUP_DIR=".backup_admin_ui_$STAMP"
mkdir -p "$BACKUP_DIR"

cp backend/app/api/advanced_routes.py "$BACKUP_DIR/advanced_routes.py"
cp frontend/app/admin/page.tsx "$BACKUP_DIR/admin_page.tsx"
cp frontend/app/globals.css "$BACKUP_DIR/globals.css"

echo "✅ Backup created: $BACKUP_DIR"

python3 - <<'PY'
from pathlib import Path

p = Path("backend/app/api/advanced_routes.py")
s = p.read_text()

if '@router.delete("/admin/users/{target_user_id}")' not in s:
    insert = r'''

@router.delete("/admin/users/{target_user_id}")
def admin_delete_user(
    target_user_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    require_admin(user)

    if target_user_id == user.id:
        raise HTTPException(status_code=400, detail="You cannot delete your own account")

    target = db.query(User).filter(User.id == target_user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    db.delete(target)
    db.commit()

    return {"status": "deleted"}
'''
    s += insert

p.write_text(s)
print("✅ DELETE admin user endpoint added")
PY

cat > frontend/app/admin/page.tsx <<'EOF'
"use client";

import { useEffect, useState } from "react";
import { api } from "../../lib/api";

export default function AdminPage() {
  const [users, setUsers] = useState<any[]>([]);
  const [message, setMessage] = useState("");

  async function loadUsers() {
    setMessage("");
    try {
      const data = await api("/admin/users");
      setUsers(data);
    } catch (e: any) {
      setMessage("فشل تحميل المستخدمين: " + e.message);
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
      setMessage("فشل التحديث: " + e.message);
    }
  }

  async function deleteUser(id: number, email: string) {
    setMessage("");

    const ok = window.confirm(`هل أنت متأكد من حذف المستخدم؟\n${email}`);
    if (!ok) return;

    try {
      await api(`/admin/users/${id}`, {
        method: "DELETE"
      });
      setMessage("تم حذف المستخدم");
      await loadUsers();
    } catch (e: any) {
      setMessage("فشل الحذف: " + e.message);
    }
  }

  useEffect(() => {
    loadUsers();
  }, []);

  return (
    <main className="container">
      <div className="card admin-users-card">
        <h1>Admin - إدارة الأصدقاء</h1>
        <p>من هنا يمكنك تفعيل أو تعطيل المستخدمين، منح صلاحية Admin، أو حذف حساب مستخدم.</p>

        {message && <div className="admin-message">{message}</div>}

        <button className="btn btn-secondary" onClick={loadUsers} style={{ marginBottom: 18 }}>
          تحديث القائمة
        </button>

        <div className="admin-users-grid">
          {users.map(u => (
            <div className="admin-user-box" key={u.id}>
              <div className="admin-user-top">
                <div>
                  <div className="admin-user-id">ID #{u.id}</div>
                  <div className="admin-user-email">{u.email}</div>
                </div>

                <div className="admin-user-badges">
                  <span className={u.is_active ? "admin-badge active" : "admin-badge inactive"}>
                    {u.is_active ? "Active" : "Disabled"}
                  </span>

                  <span className={u.is_admin ? "admin-badge admin" : "admin-badge user"}>
                    {u.is_admin ? "Admin" : "User"}
                  </span>

                  <span className={u.binance_key_configured ? "admin-badge binance" : "admin-badge missing"}>
                    {u.binance_key_configured ? "Binance OK" : "No Binance"}
                  </span>
                </div>
              </div>

              <div className="admin-user-actions">
                <button
                  className={u.is_active ? "btn btn-danger" : "btn btn-primary"}
                  onClick={() => updateUser(u.id, { is_active: !u.is_active })}
                >
                  {u.is_active ? "تعطيل" : "تفعيل"}
                </button>

                <button
                  className="btn btn-secondary"
                  onClick={() => updateUser(u.id, { is_admin: !u.is_admin })}
                >
                  {u.is_admin ? "إزالة Admin" : "تعيين Admin"}
                </button>

                <button
                  className="btn btn-danger"
                  onClick={() => deleteUser(u.id, u.email)}
                >
                  حذف
                </button>
              </div>
            </div>
          ))}
        </div>

        <p style={{ marginTop: 22 }}>
          <a href="/">العودة للوحة التحكم</a>
        </p>
      </div>
    </main>
  );
}
