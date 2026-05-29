#!/usr/bin/env bash
set -e

cd /home/nawaf511/ndsp-binance-bot

PAGE="frontend/app/page.tsx"
CSS="frontend/app/globals.css"

if [ ! -f "$PAGE" ]; then
  echo "❌ لم أجد الملف: $PAGE"
  exit 1
fi

if [ ! -f "$CSS" ]; then
  echo "❌ لم أجد الملف: $CSS"
  exit 1
fi

cp "$PAGE" "$PAGE.backup_register_hunter_$(date +%Y%m%d_%H%M%S)"
cp "$CSS" "$CSS.backup_register_hunter_$(date +%Y%m%d_%H%M%S)"

python3 - <<'PY'
from pathlib import Path

p = Path("frontend/app/page.tsx")
s = p.read_text()

# 1) Add register states after password state
old = '  const [password, setPassword] = useState("");'
new = '''  const [password, setPassword] = useState("");
  const [authMode, setAuthMode] = useState<"login" | "register">("login");
  const [registerEmail, setRegisterEmail] = useState("");
  const [registerPassword, setRegisterPassword] = useState("");
  const [registerInviteCode, setRegisterInviteCode] = useState("");'''
if old in s and "registerEmail" not in s:
    s = s.replace(old, new)

# 2) Add register function before login function
marker = '''  async function login() {'''
register_func = '''  async function registerUser() {
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

'''
if marker in s and "async function registerUser()" not in s:
    s = s.replace(marker, register_func + marker)

# 3) Replace login page block
old_block = '''  if (!getToken() || !me) {
    return (
      <main className="container">
        <div className="card" style={{ maxWidth: 520, margin: "80px auto" }}>
          <h1>NDSP Trading Bot</h1>
          <p>تسجيل الدخول إلى لوحة التحكم</p>

          <label>الإيميل</label>
          <input className="input" value={email} onChange={e => setEmail(e.target.value)} />

          <label style={{ marginTop: 12, display: "block" }}>كلمة المرور</label>
          <input className="input" type="password" value={password} onChange={e => setPassword(e.target.value)} />

          <button className="btn btn-primary" style={{ width: "100%", marginTop: 18 }} onClick={login}>
            دخول
          </button>

          {message && <p style={{ marginTop: 16 }}>{message}</p>}
        </div>
      </main>
    );
  }
'''

new_block = '''  if (!getToken() || !me) {
    return (
      <main className="container auth-page">
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
            <div className="signature-pill">Signature: hunter_ksa1</div>
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
              <label>الإيميل</label>
              <input
                className="input"
                value={email}
                onChange={e => setEmail(e.target.value)}
                placeholder="nawaf@example.com"
              />

              <label style={{ marginTop: 12, display: "block" }}>كلمة المرور</label>
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

              <label style={{ marginTop: 12, display: "block" }}>كلمة المرور</label>
              <input
                className="input"
                type="password"
                value={registerPassword}
                onChange={e => setRegisterPassword(e.target.value)}
                placeholder="8 أحرف على الأقل"
              />

              <label style={{ marginTop: 12, display: "block" }}>كود الدعوة</label>
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
'''

if old_block not in s:
    print("⚠️ لم أجد بلوك صفحة الدخول القديم. قد يكون تم تعديله سابقًا.")
else:
    s = s.replace(old_block, new_block)

p.write_text(s)
print("✅ page.tsx updated")
PY

cat >> "$CSS" <<'EOF'

/* Hunter KSA1 Premium Theme */
body {
  background:
    radial-gradient(circle at 15% 15%, rgba(34, 197, 94, 0.13), transparent 28%),
    radial-gradient(circle at 85% 20%, rgba(59, 130, 246, 0.14), transparent 30%),
    radial-gradient(circle at 50% 85%, rgba(168, 85, 247, 0.12), transparent 34%),
    linear-gradient(135deg, #020617 0%, #0f172a 52%, #020617 100%);
  min-height: 100vh;
}

body::before {
  content: "hunter_ksa1";
  position: fixed;
  inset: auto -80px 8% auto;
  font-size: clamp(54px, 13vw, 180px);
  font-weight: 900;
  letter-spacing: 6px;
  color: rgba(255, 255, 255, 0.035);
  transform: rotate(-18deg);
  pointer-events: none;
  z-index: 0;
}

body::after {
  content: "16 LAYERS • NDSP POWER MATRIX • EXECUTION ENGINE";
  position: fixed;
  top: 22%;
  left: -80px;
  font-size: clamp(18px, 3vw, 42px);
  font-weight: 800;
  letter-spacing: 4px;
  color: rgba(34, 197, 94, 0.07);
  transform: rotate(-90deg);
  transform-origin: left top;
  pointer-events: none;
  z-index: 0;
}

.container {
  position: relative;
  z-index: 1;
}

.card {
  background:
    linear-gradient(145deg, rgba(17, 24, 39, 0.94), rgba(15, 23, 42, 0.9));
  backdrop-filter: blur(12px);
  box-shadow:
    0 18px 45px rgba(0, 0, 0, 0.28),
    inset 0 1px 0 rgba(255, 255, 255, 0.035);
}

.auth-page {
  min-height: 100vh;
  display: grid;
  place-items: center;
  overflow: hidden;
}

.hunter-bg-signature {
  position: fixed;
  inset: 0;
  pointer-events: none;
  z-index: 0;
  overflow: hidden;
}

.hunter-mark {
  position: absolute;
  top: 9%;
  right: -40px;
  font-size: clamp(44px, 10vw, 155px);
  line-height: 1;
  font-weight: 950;
  letter-spacing: 7px;
  color: rgba(255, 255, 255, 0.045);
  transform: rotate(-12deg);
  text-transform: uppercase;
}

.hunter-layers {
  position: absolute;
  bottom: 10%;
  left: -30px;
  font-size: clamp(20px, 4vw, 58px);
  font-weight: 900;
  letter-spacing: 5px;
  color: rgba(34, 197, 94, 0.09);
  transform: rotate(8deg);
}

.auth-card {
  position: relative;
  width: min(760px, 100%);
  padding: clamp(24px, 5vw, 46px);
  border-radius: 30px;
  border: 1px solid rgba(148, 163, 184, 0.18);
  background:
    radial-gradient(circle at 10% 0%, rgba(34, 197, 94, 0.18), transparent 30%),
    radial-gradient(circle at 90% 15%, rgba(59, 130, 246, 0.16), transparent 35%),
    linear-gradient(145deg, rgba(15, 23, 42, 0.96), rgba(2, 6, 23, 0.92));
  box-shadow:
    0 30px 80px rgba(0, 0, 0, 0.45),
    0 0 0 1px rgba(255, 255, 255, 0.03) inset;
  overflow: hidden;
}

.auth-glow {
  position: absolute;
  width: 280px;
  height: 280px;
  top: -120px;
  left: -120px;
  background: radial-gradient(circle, rgba(34, 197, 94, 0.22), transparent 65%);
  filter: blur(4px);
}

.auth-brand {
  position: relative;
  text-align: center;
  margin-bottom: 26px;
}

.brand-kicker {
  color: #86efac;
  font-size: 13px;
  font-weight: 800;
  letter-spacing: 2px;
  text-transform: uppercase;
  margin-bottom: 10px;
}

.auth-brand h1 {
  margin: 0;
  font-size: clamp(38px, 8vw, 76px);
  letter-spacing: -2px;
}

.auth-brand p {
  color: #cbd5e1;
  line-height: 1.8;
  margin: 14px auto 0;
  max-width: 560px;
}

.signature-pill {
  display: inline-flex;
  margin-top: 16px;
  padding: 8px 14px;
  border-radius: 999px;
  background: rgba(34, 197, 94, 0.12);
  color: #86efac;
  border: 1px solid rgba(34, 197, 94, 0.25);
  font-weight: 800;
}

.auth-switch {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
  background: rgba(2, 6, 23, 0.55);
  border: 1px solid rgba(148, 163, 184, 0.12);
  border-radius: 18px;
  padding: 8px;
  margin-bottom: 20px;
}

.auth-switch button {
  border: 0;
  border-radius: 14px;
  padding: 13px;
  background: transparent;
  color: #cbd5e1;
  cursor: pointer;
  font-weight: 900;
}

.auth-switch button.active {
  background: linear-gradient(135deg, #22c55e, #16a34a);
  color: #052e16;
}

.auth-form label {
  color: #e5e7eb;
  font-weight: 800;
}

.auth-main-btn {
  width: 100%;
  margin-top: 18px;
  font-size: 17px;
}

.auth-message {
  margin-top: 16px;
  padding: 13px;
  border-radius: 14px;
  background: rgba(15, 23, 42, 0.72);
  border: 1px solid rgba(148, 163, 184, 0.14);
  color: #e5e7eb;
}

.auth-warning {
  margin-top: 16px;
  color: #fbbf24;
  font-size: 13px;
  text-align: center;
}

.nav button {
  box-shadow: 0 10px 24px rgba(0, 0, 0, 0.18);
}

.nav button.active {
  background: linear-gradient(135deg, #22c55e, #16a34a);
}

@media (max-width: 700px) {
  .auth-card {
    border-radius: 22px;
  }

  .auth-brand h1 {
    font-size: 42px;
  }

  .hunter-mark {
    top: 4%;
    right: -30px;
    letter-spacing: 3px;
  }

  .hunter-layers {
    bottom: 4%;
    left: -20px;
    letter-spacing: 2px;
  }
}
