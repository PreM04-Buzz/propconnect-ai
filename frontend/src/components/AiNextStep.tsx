import { useEffect, useState } from "react";
import { api, errorMessage, type Suggestion } from "../api/client";
import { shortDate } from "../lib/format";

const ACTION_LABEL: Record<string, string> = {
  call: "Call", email: "Email", text: "Text", schedule_viewing: "Schedule viewing", send_listings: "Send listings",
  follow_up_later: "Follow up later", update_profile: "Update profile",
};

export function AiNextStep({ leadId, onDecided }: { leadId: number; onDecided: () => void }) {
  const [history, setHistory] = useState<Suggestion[]>([]);
  const [current, setCurrent] = useState<Suggestion | null>(null);
  const [draft, setDraft] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    api.GET("/api/leads/{lead_id}/ai/suggestions", { params: { path: { lead_id: leadId } } }).then(({ data }) => {
      if (!data) return;
      setHistory(data);
      const open = data.find((s) => s.status === "suggested");
      if (open) {
        setCurrent(open);
        setDraft(open.draft_message);
      }
    });
  }, [leadId]);

  async function ask() {
    setLoading(true);
    setError(null);
    const { data, error } = await api.POST("/api/leads/{lead_id}/ai/next-step", { params: { path: { lead_id: leadId } } });
    setLoading(false);
    if (!data) return setError(errorMessage(error));
    setCurrent(data);
    setDraft(data.draft_message);
    setHistory((h) => [data, ...h]);
  }

  async function decide(status: "accepted" | "dismissed") {
    if (!current) return;
    const { data, error } = await api.POST("/api/ai/suggestions/{suggestion_id}/decision", {
      params: { path: { suggestion_id: current.id } },
      body: { status, draft_message: draft !== current.draft_message ? draft : null },
    });
    if (!data) return setError(errorMessage(error));
    setHistory((h) => h.map((s) => (s.id === data.id ? data : s)));
    setCurrent(null);
    onDecided();
  }

  return (
    <div className="card ai-card">
      <div className="ai-head">
        <div>
          <h2>AI next step</h2>
          <p className="muted small">Reads this client's profile, activity and shortlist, then suggests one action. You decide.</p>
        </div>
        <button onClick={ask} disabled={loading}>{loading ? "Thinking…" : current ? "Ask again" : "Suggest next step"}</button>
      </div>
      {error && <p className="error">{error}</p>}
      {current && (
        <div className="ai-result">
          <div className="ai-tags">
            <span className={`badge priority-${current.intent_level}`}>{current.intent_level} intent</span>
            <span className="badge">{ACTION_LABEL[current.action_type] ?? current.action_type}</span>
            <span className="badge source" title={current.source === "rules" ? "No AI key configured or the AI was unavailable" : ""}>
              {current.source === "openai" ? `AI · ${current.model}` : "Rule-based fallback"}
            </span>
          </div>
          <p className="ai-summary">{current.summary}</p>
          <div className="ai-action">
            <span className="label">Recommended</span>
            <p>{current.recommended_action}</p>
          </div>
          <p className="muted small"><strong>Why:</strong> {current.reasoning}</p>
          <label className="draft">Draft message (edit before sending)
            <textarea rows={5} value={draft} onChange={(e) => setDraft(e.target.value)} />
          </label>
          <div className="actions">
            <button onClick={() => decide("accepted")}>Accept and log</button>
            <button className="secondary" onClick={async () => { await navigator.clipboard.writeText(draft); setCopied(true); setTimeout(() => setCopied(false), 1500); }}>
              {copied ? "Copied" : "Copy message"}
            </button>
            <button className="secondary" onClick={() => decide("dismissed")}>Dismiss</button>
          </div>
        </div>
      )}
      {!current && !loading && <p className="empty">No open suggestion. Ask for one when you're deciding what to do next.</p>}
      {history.filter((s) => s.status !== "suggested").length > 0 && (
        <details className="ai-history">
          <summary>Past suggestions ({history.filter((s) => s.status !== "suggested").length})</summary>
          <ul>
            {history.filter((s) => s.status !== "suggested").map((s) => (
              <li key={s.id}><span className={`badge ${s.status === "accepted" ? "priority-high" : ""}`}>{s.status}</span> {shortDate(s.created_at)} · {s.recommended_action}</li>
            ))}
          </ul>
        </details>
      )}
    </div>
  );
}
