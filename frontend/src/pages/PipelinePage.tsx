import { useCallback, useEffect, useState, type DragEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api, errorMessage, type LeadCard, type LeadStage } from "../api/client";
import { ScoreRing } from "../components/Badges";
import { compactMoney, relativeDays, STAGES, stageLabel } from "../lib/format";

export function PipelinePage() {
  const navigate = useNavigate();
  const [leads, setLeads] = useState<LeadCard[] | null>(null);
  const [q, setQ] = useState("");
  const [dragId, setDragId] = useState<number | null>(null);
  const [over, setOver] = useState<LeadStage | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    const { data, error } = await api.GET("/api/leads", { params: { query: { q: q || undefined } } });
    if (data) setLeads(data);
    else setError(errorMessage(error));
  }, [q]);

  useEffect(() => {
    const t = setTimeout(load, 250);
    return () => clearTimeout(t);
  }, [load]);

  async function move(leadId: number, to: LeadStage) {
    const lead = leads?.find((l) => l.id === leadId);
    if (!lead || lead.stage === to) return;
    let lost_reason: string | undefined;
    if (to === "lost") {
      lost_reason = window.prompt(`Why was ${lead.client_name}'s lead lost?`)?.trim();
      if (!lost_reason) return;
    }
    setLeads((prev) => prev?.map((l) => (l.id === leadId ? { ...l, stage: to } : l)) ?? null); // optimistic
    const { error } = await api.POST("/api/leads/{lead_id}/move", { params: { path: { lead_id: leadId } }, body: { to_stage: to, lost_reason } });
    if (error) setError(errorMessage(error));
    void load();
  }

  function onDrop(e: DragEvent, stage: LeadStage) {
    e.preventDefault();
    setOver(null);
    if (dragId != null) void move(dragId, stage);
    setDragId(null);
  }

  return (
    <section className="wide-page">
      <div className="page-head">
        <div>
          <h1>Lead pipeline</h1>
          <p className="muted">Drag a card to move a lead. Every move is saved in the lead's history.</p>
        </div>
        <input placeholder="Filter by name or city" value={q} onChange={(e) => setQ(e.target.value)} />
      </div>
      {error && <p className="error" role="alert">{error}</p>}
      <div className="board">
        {STAGES.map((stage) => {
          const cards = leads?.filter((l) => l.stage === stage) ?? [];
          return (
            <div key={stage} id={stage} className={`column stage-col-${stage} ${over === stage ? "over" : ""}`}
                 onDragOver={(e) => { e.preventDefault(); setOver(stage); }} onDragLeave={() => setOver(null)}
                 onDrop={(e) => onDrop(e, stage)}>
              <div className="column-head">
                <span>{stageLabel(stage)}</span>
                <span className="count">{cards.length}</span>
              </div>
              {cards.map((l) => (
                <article key={l.id} className="lead-card" draggable onDragStart={() => setDragId(l.id)}
                         onDragEnd={() => setDragId(null)} onClick={() => navigate(`/leads/${l.id}`)}>
                  <div className="lead-card-top">
                    <strong>{l.client_name}</strong>
                    <ScoreRing score={l.score} />
                  </div>
                  <div className="muted small">{l.preferred_city ?? "Any city"} · {compactMoney(l.budget_max)} · <span className="cap">{l.client_type}</span></div>
                  <div className="muted small">Last contact: {relativeDays(l.last_contact_at)}</div>
                  <select className="move" aria-label={`Move ${l.client_name}`} value={l.stage}
                          onClick={(e) => e.stopPropagation()} onChange={(e) => move(l.id, e.target.value as LeadStage)}>
                    {STAGES.map((s) => <option key={s} value={s}>{s === l.stage ? stageLabel(s) : `Move to ${stageLabel(s)}`}</option>)}
                  </select>
                </article>
              ))}
              {leads && cards.length === 0 && <p className="column-empty">Drop leads here</p>}
            </div>
          );
        })}
      </div>
      <p className="muted small">Scores are rule-based: financing, timeline, viewings, confirmed budget, recent contact and property interest. <Link to="/clients/new">Add a client</Link> to create a new lead.</p>
    </section>
  );
}
