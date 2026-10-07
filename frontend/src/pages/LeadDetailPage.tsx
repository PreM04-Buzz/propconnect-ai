import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api, errorMessage, type LeadDetail, type LeadStage } from "../api/client";
import { AiNextStep } from "../components/AiNextStep";
import { PriorityBadge, ScoreRing } from "../components/Badges";
import { financingLabel, money, shortDate, STAGES, stageLabel } from "../lib/format";

export function LeadDetailPage() {
  const id = Number(useParams().id);
  const [lead, setLead] = useState<LeadDetail | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    const { data, error } = await api.GET("/api/leads/{lead_id}", { params: { path: { lead_id: id } } });
    if (data) setLead(data);
    else setError(errorMessage(error, "Lead not found."));
  }, [id]);

  useEffect(() => {
    void load();
  }, [load]);

  async function move(to: LeadStage) {
    if (!lead || to === lead.stage) return;
    let lost_reason: string | undefined;
    if (to === "lost") {
      lost_reason = window.prompt("Why was this lead lost?")?.trim();
      if (!lost_reason) return;
    }
    const { data, error } = await api.POST("/api/leads/{lead_id}/move", { params: { path: { lead_id: id } }, body: { to_stage: to, lost_reason } });
    if (data) setLead(data);
    else setError(errorMessage(error));
  }

  if (error && !lead) return <p className="error">{error}</p>;
  if (!lead) return <p className="page-status">Loading…</p>;
  const c = lead.client;
  const current = STAGES.indexOf(lead.stage);

  return (
    <section>
      <p className="crumbs"><Link to="/pipeline">Pipeline</Link> / {c.first_name} {c.last_name}</p>
      <div className="page-head">
        <div className="title-row">
          <ScoreRing score={lead.score} />
          <div>
            <h1>{c.first_name} {c.last_name}</h1>
            <p className="muted">
              <span className="cap">{c.client_type}</span> · {c.preferred_city ?? "Any city"} · up to {money(c.budget_max)} · {financingLabel[c.financing_status]}
            </p>
          </div>
        </div>
        <div className="actions">
          <PriorityBadge priority={lead.priority} />
          <Link className="button secondary" to={`/clients/${c.id}`}>Client profile</Link>
        </div>
      </div>

      <ol className="stepper" aria-label="Pipeline stage">
        {STAGES.map((s, i) => (
          <li key={s}>
            <button className={`step ${s === lead.stage ? "current" : ""} ${i < current && lead.stage !== "lost" ? "done" : ""} ${s === "lost" ? "lost" : ""}`}
                    onClick={() => move(s)} aria-current={s === lead.stage ? "step" : undefined}>
              {stageLabel(s)}
            </button>
          </li>
        ))}
      </ol>
      {lead.lost_reason && <p className="notice">Lost: {lead.lost_reason}</p>}
      {error && <p className="error">{error}</p>}

      <div className="grid-2 lead-grid">
        <AiNextStep leadId={id} onDecided={load} />
        <div>
          <div className="card">
            <h2>Why this score: {lead.score ?? "—"}/100</h2>
            <ul className="score-bars">
              {lead.score_breakdown.map((s) => (
                <li key={s.factor}>
                  <div className="score-label"><span>{s.factor}</span><span>{s.points}/{s.max_points}</span></div>
                  <div className="bar"><div style={{ width: `${(s.points / s.max_points) * 100}%` }} /></div>
                  <span className="muted small">{s.reason}</span>
                </li>
              ))}
            </ul>
          </div>
          <div className="card">
            <h2>Stage history</h2>
            <ul className="timeline">
              {[...lead.history].reverse().map((h) => (
                <li key={h.id}>
                  <span className={`dot stage-dot-${h.to_stage}`} />
                  <div>
                    <strong>{h.from_stage ? `${stageLabel(h.from_stage)} → ${stageLabel(h.to_stage)}` : `Created as ${stageLabel(h.to_stage)}`}</strong>
                    <span className="muted small"> {shortDate(h.changed_at)}</span>
                  </div>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </div>
    </section>
  );
}
