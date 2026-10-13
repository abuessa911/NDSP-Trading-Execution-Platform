export default function AdminBlocked() {
  // These routes are deliberately outside the limited M1 health/audit views.
  return (
    <section className="panel" aria-label="Administrative feature unavailable">
      <span className="tag">NOT AVAILABLE IN M1</span>
      <h2>This administrator view is not enabled</h2>
      <p>Only read-only control-plane health, tenant user directory and tenant-scoped audit views are in the current M1 administrator scope.</p>
      <p className="muted">This route makes no privileged data request. Other administrator capabilities require a separately approved implementation.</p>
    </section>
  );
}