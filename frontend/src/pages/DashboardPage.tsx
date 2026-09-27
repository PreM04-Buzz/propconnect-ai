import { useAuth } from "../auth/AuthContext";

const stages = ["New", "Contacted", "Qualified", "Proposal", "Negotiation", "Won", "Lost"];

export function DashboardPage() {
  const { user } = useAuth();
  const firstName = user?.full_name.split(" ")[0] ?? "";
  return (
    <section>
      <h1>Welcome, {firstName}</h1>
      <p className="muted">
        The foundation is in place. Leads, clients and listings arrive in phase 2, and this
        dashboard fills in with live metrics in phase 6.
      </p>
      <h2>Lead pipeline</h2>
      <ol className="pipeline" aria-label="Pipeline stages">
        {stages.map((s) => (
          <li key={s}>
            <span>{s}</span>
            <strong>0</strong>
          </li>
        ))}
      </ol>
    </section>
  );
}
