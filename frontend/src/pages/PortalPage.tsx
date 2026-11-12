import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { clientTokenStore, errorMessage, portalApi, setClientUnauthorizedHandler, type MessageRead, type PortalOverview } from "../api/client";
import { MessageThread } from "../components/MessageThread";
import { money } from "../lib/format";

const offerWords: Record<string, string> = {
  submitted: "Sent to the seller", countered: "The seller made a counter-offer", accepted: "Accepted",
  rejected: "Not accepted", withdrawn: "Withdrawn",
};
const kindWords: Record<string, string> = { viewing: "Viewing", meeting: "Meeting", follow_up: "Call with your agent" };
const longWhen = (iso: string) =>
  new Date(iso).toLocaleString("en-US", { weekday: "long", month: "long", day: "numeric", hour: "numeric", minute: "2-digit" });

/** The client's own page: progress, viewings, offers and messages. */
export function PortalPage() {
  const navigate = useNavigate();
  const [o, setO] = useState<PortalOverview | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [channel, setChannel] = useState<"agent" | "broker">("agent");
  const [messages, setMessages] = useState<MessageRead[] | null>(null);

  const signOut = useCallback(() => {
    clientTokenStore.clear();
    navigate("/portal/login", { replace: true });
  }, [navigate]);

  useEffect(() => {
    setClientUnauthorizedHandler(signOut);
    if (!clientTokenStore.get()) signOut();
  }, [signOut]);

  const loadOverview = useCallback(async () => {
    try {
      const { data, error: e } = await portalApi.GET("/api/portal/me");
      if (e) return setError(errorMessage(e));
      setO(data ?? null);
      if (data && !data.agent) setChannel("broker");
    } catch {
      setError("Can’t reach the server right now. It may be waking up: try again in a minute.");
    }
  }, []);

  const loadMessages = useCallback(async (ch: "agent" | "broker") => {
    const { data } = await portalApi.GET("/api/portal/messages", { params: { query: { channel: ch } } });
    if (data) setMessages(data);
  }, []);

  useEffect(() => {
    void loadOverview();
  }, [loadOverview]);

  useEffect(() => {
    setMessages(null);
    void loadMessages(channel).then(loadOverview);
    const t = setInterval(() => void loadMessages(channel), 30000);  // new replies show up without a refresh
    return () => clearInterval(t);
  }, [channel, loadMessages, loadOverview]);

  async function send(body: string): Promise<string | null> {
    const { error: e } = await portalApi.POST("/api/portal/messages", { body: { channel, body } });
    if (e) return errorMessage(e);
    await loadMessages(channel);
    return null;
  }

  return (
    <div className="portal">
      <header className="portal-top">
        <span className="wl-brand">PropConnect <span>AI</span></span>
        <div className="portal-who">
          {o && <span>Hi, {o.first_name}</span>}
          <button type="button" className="link-button" onClick={signOut}>Sign out</button>
        </div>
      </header>
      <main className="portal-main">
        {error && <p className="error" role="alert">{error}</p>}
        {!o ? <p className="muted">Loading your page…</p> : (
          <>
            <section className="card portal-progress">
              <p className="wl-kicker">Your home search</p>
              <h1>{o.stage_label}</h1>
              <p className="portal-desc">{o.stage_description}</p>
              <ol className="psteps" aria-label="Your progress">
                {o.steps.map((s) => (
                  <li key={s.key} className={`pstep pstep-${s.state}`} aria-current={s.state === "current" ? "step" : undefined}>
                    <span className="pstep-dot" aria-hidden="true">{s.state === "done" ? "✓" : ""}</span>
                    <span className="pstep-label">{s.label}</span>
                  </li>
                ))}
              </ol>
            </section>

            <div className="portal-grid">
              <section className="card">
                <h2>Your agent</h2>
                {o.agent ? (
                  <>
                    <p className="portal-agent">{o.agent.name}</p>
                    <p><a href={`mailto:${o.agent.email}`}>{o.agent.email}</a></p>
                  </>
                ) : <p className="muted">A broker is choosing the best agent for you. You can message the broker below meanwhile.</p>}
              </section>
              <section className="card">
                <h2>Coming up</h2>
                {o.appointments.length === 0 ? <p className="muted">Nothing booked yet. Your agent will arrange viewings with you.</p> : (
                  <ul className="portal-list">
                    {o.appointments.map((a, i) => (
                      <li key={i}><strong>{kindWords[a.kind] ?? a.kind}</strong>{a.address ? ` at ${a.address}` : ""}
                        <span className="muted small">{longWhen(a.starts_at)}</span></li>
                    ))}
                  </ul>
                )}
              </section>
              <section className="card">
                <h2>Your offers</h2>
                {o.offers.length === 0 ? <p className="muted">No offers yet.</p> : (
                  <ul className="portal-list">
                    {o.offers.map((f, i) => (
                      <li key={i}><strong>{money(f.amount)}</strong>{f.address ? ` for ${f.address}` : ""}
                        <span className="muted small">{offerWords[f.status] ?? f.status}
                          {f.status === "countered" && f.counter_amount ? `: ${money(f.counter_amount)}` : ""}</span></li>
                    ))}
                  </ul>
                )}
              </section>
            </div>

            <section className="card portal-messages">
              <h2>Messages</h2>
              <div className="tabs" role="tablist">
                <button role="tab" aria-selected={channel === "agent"} className={channel === "agent" ? "tab active" : "tab"}
                        onClick={() => setChannel("agent")}>
                  My agent{o.unread.agent ? <span className="nav-count">{o.unread.agent}</span> : null}
                </button>
                <button role="tab" aria-selected={channel === "broker"} className={channel === "broker" ? "tab active" : "tab"}
                        onClick={() => setChannel("broker")}>
                  The broker{o.unread.broker ? <span className="nav-count">{o.unread.broker}</span> : null}
                </button>
              </div>
              <MessageThread messages={messages} mine="client" onSend={send}
                             placeholder={channel === "agent" ? "Write to your agent…" : "Write to the broker…"}
                             disabled={channel === "agent" && !o.agent ? "You don’t have an agent yet. Write to the broker instead." : null}
                             note={channel === "broker" ? "Messages to the broker are private: your agent doesn’t see them." : undefined} />
            </section>
          </>
        )}
      </main>
    </div>
  );
}
