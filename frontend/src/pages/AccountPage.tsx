import { useState, type FormEvent } from "react";
import { api, errorMessage } from "../api/client";
import { useAuth } from "../auth/AuthContext";

export function AccountPage() {
  const { user } = useAuth();
  const [v, setV] = useState({ current: "", next: "", again: "" });
  const [message, setMessage] = useState<{ ok: boolean; text: string } | null>(null);

  async function submit(e: FormEvent) {
    e.preventDefault();
    if (v.next !== v.again) return setMessage({ ok: false, text: "The two new passwords don't match." });
    const { error } = await api.POST("/api/users/me/password", { body: { current_password: v.current, new_password: v.next } });
    if (error) return setMessage({ ok: false, text: errorMessage(error) });
    setV({ current: "", next: "", again: "" });
    setMessage({ ok: true, text: "Password changed. Use the new one next time you sign in." });
  }

  return (
    <section className="narrow">
      <h1>Your account</h1>
      <p className="muted">{user?.full_name} · {user?.email} · {user?.role === "admin" ? "Broker / admin" : "Agent"}</p>
      <form className="card form-card" onSubmit={submit}>
        <h2>Change password</h2>
        <label>Current password<input type="password" autoComplete="current-password" required value={v.current} onChange={(e) => setV({ ...v, current: e.target.value })} /></label>
        <label>New password (8+ characters)<input type="password" autoComplete="new-password" required minLength={8} value={v.next} onChange={(e) => setV({ ...v, next: e.target.value })} /></label>
        <label>New password again<input type="password" autoComplete="new-password" required minLength={8} value={v.again} onChange={(e) => setV({ ...v, again: e.target.value })} /></label>
        {message && <p className={message.ok ? "notice" : "error"} role="alert">{message.text}</p>}
        <div className="actions"><button type="submit">Change password</button></div>
      </form>
    </section>
  );
}
