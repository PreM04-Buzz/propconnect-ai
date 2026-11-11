import { useCallback, useEffect, useState, type FormEvent } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { api, errorMessage, type AssignmentRow, type TeamMember, type UserRole } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { money, shortDate } from "../lib/format";

const roleLabel = (r: UserRole) => (r === "admin" ? "Broker" : "Agent");

/** What happened to the "meet your agent" email for this client and their current agent. */
function introBadge(r: AssignmentRow) {
  if (!r.agent_id) return <span className="muted small">Sent when assigned</span>;
  if (r.intro_email === "sent") return <span className="badge intro-sent">Sent</span>;
  if (r.intro_email === "failed") return <span className="badge intro-failed">Failed</span>;
  if (!r.email) return <span className="muted small">No email address</span>;
  return <span className="muted small">Not sent</span>;
}

/** Broker-only: assign clients to agents, and manage the team. */
export function AdminPage() {
  const [params, setParams] = useSearchParams();
  const tab = params.get("tab") === "team" ? "team" : "assign";
  return (
    <section className="wide-page">
      <div className="page-head">
        <div>
          <h1>Admin</h1>
          <p className="muted">Decide who looks after each client, and manage your brokers and agents.</p>
        </div>
      </div>
      <div className="tabs" role="tablist">
        <button role="tab" aria-selected={tab === "assign"} className={tab === "assign" ? "tab active" : "tab"}
                onClick={() => setParams({ tab: "assign" })}>Assign clients</button>
        <button role="tab" aria-selected={tab === "team"} className={tab === "team" ? "tab active" : "tab"}
                onClick={() => setParams({ tab: "team" })}>Team</button>
      </div>
      {tab === "assign" ? <AssignClients /> : <Team />}
    </section>
  );
}

function AssignClients() {
  const [show, setShow] = useState<"unassigned" | "all">("unassigned");
  const [rows, setRows] = useState<AssignmentRow[] | null>(null);
  const [team, setTeam] = useState<TeamMember[]>([]);
  const [pick, setPick] = useState<Record<number, string>>({});
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null);

  const load = useCallback(async () => {
    const [r, t] = await Promise.all([
      api.GET("/api/admin/clients", { params: { query: { show } } }),
      api.GET("/api/admin/team"),
    ]);
    if (r.data) setRows(r.data);
    if (t.data) setTeam(t.data.filter((m) => m.is_active));
  }, [show]);

  useEffect(() => {
    void load();
  }, [load]);

  async function assign(row: AssignmentRow) {
    const agentId = Number(pick[row.client_id] ?? row.agent_id ?? 0);
    if (!agentId) return setMsg({ ok: false, text: `Choose who should look after ${row.client_name}.` });
    const { data, error } = await api.POST("/api/admin/clients/{client_id}/assign", {
      params: { path: { client_id: row.client_id } }, body: { agent_id: agentId },
    });
    if (error) return setMsg({ ok: false, text: errorMessage(error) });
    const moved = data.moved_appointments ? ` (${data.moved_appointments} upcoming appointment${data.moved_appointments > 1 ? "s" : ""} moved too)` : "";
    const mail = data.email_status === "sent"
      ? ` We emailed ${row.email} to introduce ${data.agent_name}.`
      : data.email_status === "failed"
        ? ` The introduction email couldn’t be sent (${data.email_detail}). It will be retried if you assign again.`
        : row.email ? ` No email was sent: ${data.email_detail}` : "";
    setMsg({ ok: data.email_status !== "failed", text: `${row.client_name} is now with ${data.agent_name}${moved}.${mail}` });
    void load();
  }

  const workload = (m: TeamMember) => `${m.full_name} (${roleLabel(m.role)}, ${m.clients} client${m.clients === 1 ? "" : "s"})`;
  return (
    <>
      <div className="assign-head">
        <p className="muted">
          {show === "unassigned"
            ? "Requests from the website form wait here until you give them to someone. When you assign a client, they get one email introducing their agent."
            : "Every client and who looks after them. Reassigning moves their leads and upcoming appointments too."}
        </p>
        <select value={show} onChange={(e) => setShow(e.target.value as "unassigned" | "all")} aria-label="Which clients">
          <option value="unassigned">Waiting for an agent</option>
          <option value="all">All clients</option>
        </select>
      </div>
      {msg && <p className={msg.ok ? "notice" : "error"} role="status">{msg.text}</p>}
      <div className="table-wrap">
        <table className="table">
          <thead>
            <tr><th>Client</th><th>Wants</th><th>Where</th><th>Budget up to</th><th>Received</th><th>Looked after by</th><th>Intro email</th><th /></tr>
          </thead>
          <tbody>
            {rows?.map((r) => (
              <tr key={r.client_id}>
                <td>
                  {r.lead_id ? <Link to={`/leads/${r.lead_id}`}>{r.client_name}</Link> : r.client_name}
                  {r.from_website && <span className="badge source-web">Website</span>}
                  <div className="muted small">{r.email}{r.phone ? ` · ${r.phone}` : ""}</div>
                </td>
                <td className="cap">{r.client_type === "both" ? "Buy and sell" : r.client_type === "seller" ? "Sell" : "Buy"}</td>
                <td>{r.preferred_city ?? "—"}</td>
                <td>{money(r.budget_max)}</td>
                <td>{shortDate(r.created_at)}</td>
                <td>
                  <select value={pick[r.client_id] ?? (r.agent_id ? String(r.agent_id) : "")}
                          onChange={(e) => setPick({ ...pick, [r.client_id]: e.target.value })}
                          aria-label={`Who looks after ${r.client_name}`}>
                    <option value="">{r.agent_id ? "—" : "Not assigned yet"}</option>
                    {team.map((m) => <option key={m.id} value={m.id}>{workload(m)}</option>)}
                  </select>
                </td>
                <td>{introBadge(r)}</td>
                <td>
                  <button type="button" className="secondary"
                          disabled={!pick[r.client_id] || pick[r.client_id] === String(r.agent_id ?? "")}
                          onClick={() => assign(r)}>{r.agent_id ? "Move" : "Assign"}</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {rows && rows.length === 0 && (
          <p className="empty">{show === "unassigned" ? "No new requests waiting. Everyone has an agent." : "No clients yet."}</p>
        )}
      </div>
      <p className="muted small">Clients can send a request from <a href={`${import.meta.env.BASE_URL}start`} target="_blank" rel="noreferrer">the public form</a>. Share that link on flyers, email signatures or social media.</p>
    </>
  );
}

function Team() {
  const { user } = useAuth();
  const [team, setTeam] = useState<TeamMember[]>([]);
  const [form, setForm] = useState({ full_name: "", email: "", password: "", role: "agent" as UserRole });
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null);
  const [saving, setSaving] = useState(false);

  const load = useCallback(async () => {
    const { data, error } = await api.GET("/api/admin/team");
    if (data) setTeam(data);
    else setMsg({ ok: false, text: errorMessage(error) });
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  async function add(e: FormEvent) {
    e.preventDefault();
    setSaving(true);
    const { error } = await api.POST("/api/users", { body: { ...form, email: form.email.trim() } });
    setSaving(false);
    if (error) return setMsg({ ok: false, text: errorMessage(error) });
    setMsg({ ok: true, text: `${form.full_name} can now sign in with ${form.email} and the temporary password. Ask them to change it on their Account page.` });
    setForm({ full_name: "", email: "", password: "", role: "agent" });
    void load();
  }

  async function update(m: TeamMember, body: { role?: UserRole; is_active?: boolean }) {
    if (body.is_active === false && !window.confirm(`Deactivate ${m.full_name}? They won’t be able to sign in. Their ${m.clients} client${m.clients === 1 ? "" : "s"} stay with them until you move them.`)) return;
    const { error } = await api.PATCH("/api/users/{user_id}", { params: { path: { user_id: m.id } }, body });
    if (error) return setMsg({ ok: false, text: errorMessage(error) });
    setMsg(null);
    void load();
  }

  return (
    <>
      <form className="card form-card team-form" onSubmit={add}>
        <h2>Add a broker or agent</h2>
        <div className="form-grid">
          <label>Full name<input required maxLength={120} value={form.full_name} onChange={(e) => setForm({ ...form, full_name: e.target.value })} /></label>
          <label>Email<input required type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} /></label>
          <label>Temporary password<input required type="password" minLength={8} autoComplete="new-password" placeholder="8+ characters"
                 value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} /></label>
          <label>Role
            <select value={form.role} onChange={(e) => setForm({ ...form, role: e.target.value as UserRole })}>
              <option value="agent">Agent: sees only their own clients</option>
              <option value="admin">Broker: sees everyone, manages the team</option>
            </select>
          </label>
        </div>
        <div className="actions"><button type="submit" disabled={saving}>{saving ? "Adding…" : "Add to team"}</button></div>
      </form>
      {msg && <p className={msg.ok ? "notice" : "error"} role="status">{msg.text}</p>}
      <div className="table-wrap">
        <table className="table">
          <thead><tr><th>Name</th><th>Role</th><th>Clients</th><th>Open leads</th><th>Upcoming</th><th>Status</th><th /></tr></thead>
          <tbody>
            {team.map((m) => {
              const me = m.id === user?.id;
              return (
                <tr key={m.id} className={m.is_active ? "" : "row-muted"}>
                  <td><strong>{m.full_name}</strong>{me && <span className="badge">You</span>}<div className="muted small">{m.email}</div></td>
                  <td>
                    <select value={m.role} disabled={me} onChange={(e) => update(m, { role: e.target.value as UserRole })}
                            aria-label={`Role for ${m.full_name}`}>
                      <option value="agent">Agent</option><option value="admin">Broker</option>
                    </select>
                  </td>
                  <td>{m.clients}</td>
                  <td>{m.open_leads}</td>
                  <td>{m.upcoming_appointments}</td>
                  <td>{m.is_active ? "Active" : "Deactivated"}</td>
                  <td>
                    {!me && (m.is_active
                      ? <button type="button" className="link-button" onClick={() => update(m, { is_active: false })}>Deactivate</button>
                      : <button type="button" className="link-button" onClick={() => update(m, { is_active: true })}>Reactivate</button>)}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </>
  );
}
