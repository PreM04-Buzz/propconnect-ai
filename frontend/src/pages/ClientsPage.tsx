import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api, errorMessage, type ClientListItem, type LeadStage } from "../api/client";
import { PriorityBadge, StageBadge } from "../components/Badges";
import { financingLabel, money, STAGES, stageLabel } from "../lib/format";

export function ClientsPage() {
  const navigate = useNavigate();
  const [rows, setRows] = useState<ClientListItem[] | null>(null);
  const [q, setQ] = useState("");
  const [type, setType] = useState("");
  const [stage, setStage] = useState("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const t = setTimeout(async () => {
      const { data, error } = await api.GET("/api/clients", {
        params: { query: { q: q || undefined, client_type: type || undefined, stage: (stage || undefined) as LeadStage | undefined } },
      });
      if (data) setRows(data);
      else setError(errorMessage(error));
    }, 250);
    return () => clearTimeout(t);
  }, [q, type, stage]);

  return (
    <section>
      <div className="page-head">
        <div>
          <h1>Clients</h1>
          <p className="muted">Buyers and sellers you're working with.</p>
        </div>
        <button onClick={() => navigate("/clients/new")}>Add client</button>
      </div>
      <div className="filters">
        <input className="grow" placeholder="Search name, email, phone or city" value={q} onChange={(e) => setQ(e.target.value)} />
        <select value={type} onChange={(e) => setType(e.target.value)}>
          <option value="">All types</option><option value="buyer">Buyers</option><option value="seller">Sellers</option><option value="both">Both</option>
        </select>
        <select value={stage} onChange={(e) => setStage(e.target.value)}>
          <option value="">All stages</option>
          {STAGES.map((s) => <option key={s} value={s}>{stageLabel(s)}</option>)}
        </select>
      </div>
      {error && <p className="error">{error}</p>}
      <div className="table-wrap">
        <table className="table">
          <thead>
            <tr><th>Name</th><th>Type</th><th>Looking in</th><th>Budget up to</th><th>Financing</th><th>Stage</th><th>Priority</th></tr>
          </thead>
          <tbody>
            {rows?.map((c) => (
              <tr key={c.id} className="clickable" onClick={() => navigate(`/clients/${c.id}`)}>
                <td><Link to={`/clients/${c.id}`} onClick={(e) => e.stopPropagation()}><strong>{c.first_name} {c.last_name}</strong></Link>
                  <div className="muted small">{c.email ?? c.phone ?? ""}</div></td>
                <td className="cap">{c.client_type}</td>
                <td>{c.preferred_city ?? "—"}</td>
                <td>{money(c.budget_max)}</td>
                <td>{financingLabel[c.financing_status]}</td>
                <td><StageBadge stage={c.lead_stage} /></td>
                <td><PriorityBadge priority={c.lead_priority} /></td>
              </tr>
            ))}
          </tbody>
        </table>
        {rows && rows.length === 0 && <p className="empty">No clients match. Try a different search or add a client.</p>}
        {!rows && !error && <p className="empty">Loading…</p>}
      </div>
    </section>
  );
}
