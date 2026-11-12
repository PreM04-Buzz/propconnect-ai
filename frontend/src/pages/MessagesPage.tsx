import { useCallback, useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { api, errorMessage, type Conversation, type MessageRead } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { MessageThread } from "../components/MessageThread";

const ago = (iso: string) => new Date(iso).toLocaleString("en-US", { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" });

/** Staff inbox: clients' messages from the portal. Agents see their clients' agent conversations;
 *  brokers see every conversation, including the private "broker" ones. */
export function MessagesPage() {
  const { user } = useAuth();
  const [params, setParams] = useSearchParams();
  const [convs, setConvs] = useState<Conversation[] | null>(null);
  const [thread, setThread] = useState<MessageRead[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const clientId = Number(params.get("client")) || null;
  const channel = (params.get("channel") === "broker" ? "broker" : "agent") as "agent" | "broker";

  const loadConvs = useCallback(async () => {
    const { data, error: e } = await api.GET("/api/messages/conversations");
    if (e) setError(errorMessage(e));
    else setConvs(data ?? []);
  }, []);

  const loadThread = useCallback(async () => {
    if (!clientId) return setThread(null);
    const { data, error: e } = await api.GET("/api/messages/{client_id}/{channel}", {
      params: { path: { client_id: clientId, channel } },
    });
    if (e) setError(errorMessage(e));
    else setThread(data ?? []);
  }, [clientId, channel]);

  useEffect(() => {
    void loadConvs();
    const t = setInterval(() => void loadConvs(), 30000);
    return () => clearInterval(t);
  }, [loadConvs]);

  useEffect(() => {
    setThread(null);
    void loadThread().then(loadConvs);
  }, [loadThread, loadConvs]);

  async function reply(body: string): Promise<string | null> {
    if (!clientId) return "Pick a conversation first.";
    const { error: e } = await api.POST("/api/messages/{client_id}/{channel}", {
      params: { path: { client_id: clientId, channel } }, body: { body },
    });
    if (e) return errorMessage(e);
    await loadThread();
    await loadConvs();
    return null;
  }

  const open = convs?.find((c) => c.client_id === clientId && c.channel === channel);
  return (
    <section className="wide-page">
      <div className="page-head">
        <div>
          <h1>Messages</h1>
          <p className="muted">Messages clients send from their portal.
            {user?.role === "admin" ? " As a broker you also see the private “broker” conversations." : ""}</p>
        </div>
      </div>
      {error && <p className="error" role="alert">{error}</p>}
      <div className="inbox">
        <div className="inbox-list" aria-label="Conversations">
          {convs === null ? <p className="muted">Loading…</p> : convs.length === 0 ? (
            <p className="empty">No messages yet. Invite clients to the portal from their client page.</p>
          ) : convs.map((c) => {
            const active = c.client_id === clientId && c.channel === channel;
            return (
              <button type="button" key={`${c.client_id}-${c.channel}`} className={`conv ${active ? "conv-active" : ""}`}
                      onClick={() => setParams({ client: String(c.client_id), channel: c.channel })}>
                <span className="conv-top">
                  <strong>{c.client_name}</strong>
                  {c.channel === "broker" && <span className="badge source-web">To broker</span>}
                  {c.unread > 0 && <span className="nav-count" aria-label={`${c.unread} unread`}>{c.unread}</span>}
                </span>
                <span className="conv-body">{c.last_sender === "staff" ? "You: " : ""}{c.last_body}</span>
                <span className="muted small">{ago(c.last_at)}{c.agent_name && c.channel === "agent" && user?.role === "admin" ? ` · ${c.agent_name}` : ""}</span>
              </button>
            );
          })}
        </div>
        <div className="inbox-thread card">
          {!clientId ? <p className="muted">Choose a conversation.</p> : (
            <>
              <div className="inbox-head">
                <h2>{open?.client_name ?? "Conversation"}</h2>
                <Link to={`/clients/${clientId}`}>Client page</Link>
              </div>
              <MessageThread messages={thread} mine="staff" onSend={reply} placeholder="Write a reply…"
                             note={channel === "broker" ? "This conversation is private from the client’s agent." : undefined} />
            </>
          )}
        </div>
      </div>
    </section>
  );
}
