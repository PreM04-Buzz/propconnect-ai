import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, errorMessage, type PortalStatus } from "../api/client";
import { shortDate } from "../lib/format";

/** On a client's page: invite them to the portal, and see whether they use it. */
export function ClientPortalCard({ clientId, hasEmail }: { clientId: number; hasEmail: boolean }) {
  const [status, setStatus] = useState<PortalStatus | null>(null);
  const [link, setLink] = useState<string | null>(null);
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null);
  const [busy, setBusy] = useState(false);
  const [copied, setCopied] = useState(false);

  const load = () =>
    api.GET("/api/clients/{client_id}/portal", { params: { path: { client_id: clientId } } }).then(({ data }) => data && setStatus(data));
  useEffect(() => {
    void load();
  }, [clientId]); // eslint-disable-line react-hooks/exhaustive-deps

  async function invite() {
    setBusy(true);
    setMsg(null);
    const { data, error } = await api.POST("/api/clients/{client_id}/portal-invite", { params: { path: { client_id: clientId } } });
    setBusy(false);
    if (error || !data) return setMsg({ ok: false, text: errorMessage(error) });
    setLink(data.invite_url);
    setCopied(false);
    setMsg({
      ok: true,
      text: data.email_status === "sent"
        ? `We emailed the invitation. The link works once and expires on ${shortDate(data.expires_at)}.`
        : `Copy the link below and send it to the client yourself (the email wasn’t sent: ${data.email_detail.replace(/\.$/, "")}). It expires on ${shortDate(data.expires_at)}.`,
    });
    void load();
  }

  async function copy() {
    if (!link) return;
    try {
      await navigator.clipboard.writeText(link);
      setCopied(true);
    } catch {
      setCopied(false);
    }
  }

  const state = !status ? "…" : status.active
    ? `Active${status.last_login_at ? `, last signed in ${shortDate(status.last_login_at)}` : ""}`
    : status.invited ? `Invited, link expires ${shortDate(status.invite_expires_at)}` : "Not invited yet";

  return (
    <div className="card">
      <h2>Client portal</h2>
      <p className="muted">The client can follow their progress, see viewings and offers, and message you.</p>
      <p><strong>{state}</strong></p>
      {!hasEmail ? <p className="muted small">Add the client’s email address to invite them.</p> : (
        <div className="actions">
          <button type="button" className="secondary" disabled={busy} onClick={invite}>
            {busy ? "Creating link…" : status?.active ? "Send a password reset link" : status?.invited ? "Send a new link" : "Invite to client portal"}
          </button>
          <Link to={`/messages?client=${clientId}&channel=agent`}>Open messages</Link>
        </div>
      )}
      {msg && <p className={msg.ok ? "notice" : "error"} role="status">{msg.text}</p>}
      {link && (
        <div className="invite-link">
          <input readOnly value={link} aria-label="Invitation link" onFocus={(e) => e.currentTarget.select()} />
          <button type="button" className="secondary" onClick={copy}>{copied ? "Copied" : "Copy"}</button>
        </div>
      )}
    </div>
  );
}
