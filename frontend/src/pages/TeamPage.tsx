import { useEffect, useState, type FormEvent } from "react";
import { api, errorMessage, type User, type UserRole } from "../api/client";

export function TeamPage() {
  const [users, setUsers] = useState<User[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [form, setForm] = useState({ full_name: "", email: "", password: "", role: "agent" as UserRole });
  const [saving, setSaving] = useState(false);

  async function load() {
    const { data, error } = await api.GET("/api/users");
    if (data) setUsers(data);
    else setError(errorMessage(error));
  }

  useEffect(() => {
    void load();
  }, []);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSaving(true);
    const { error } = await api.POST("/api/users", { body: form });
    setSaving(false);
    if (error) return setError(errorMessage(error));
    setForm({ full_name: "", email: "", password: "", role: "agent" });
    void load();
  }

  return (
    <section>
      <h1>Team</h1>
      <p className="muted">Create accounts for agents on your team. Only brokers and admins see this page.</p>

      <form className="inline-form" onSubmit={handleSubmit}>
        <input placeholder="Full name" required value={form.full_name}
               onChange={(e) => setForm({ ...form, full_name: e.target.value })} />
        <input placeholder="Email" type="email" required value={form.email}
               onChange={(e) => setForm({ ...form, email: e.target.value })} />
        <input placeholder="Temporary password (8+ characters)" type="password" required minLength={8}
               value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} />
        <select value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value as UserRole })}>
          <option value="agent">Agent</option>
          <option value="admin">Broker / admin</option>
        </select>
        <button type="submit" disabled={saving}>{saving ? "Adding…" : "Add team member"}</button>
      </form>
      {error && <p className="error" role="alert">{error}</p>}

      <table className="table">
        <thead>
          <tr><th>Name</th><th>Email</th><th>Role</th><th>Status</th></tr>
        </thead>
        <tbody>
          {users.map((u) => (
            <tr key={u.id}>
              <td>{u.full_name}</td>
              <td>{u.email}</td>
              <td>{u.role === "admin" ? "Broker / admin" : "Agent"}</td>
              <td>{u.is_active ? "Active" : "Deactivated"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}
