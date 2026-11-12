import { useEffect, useRef, useState, type FormEvent } from "react";
import type { MessageRead } from "../api/client";

const when = (iso: string) =>
  new Date(iso).toLocaleString("en-US", { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" });

/** A conversation and a reply box. "mine" says which side is speaking (client or staff). */
export function MessageThread({ messages, mine, onSend, placeholder, disabled, note }: {
  messages: MessageRead[] | null;
  mine: "client" | "staff";
  onSend: (body: string) => Promise<string | null>;
  placeholder: string;
  disabled?: string | null;
  note?: string;
}) {
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const list = useRef<HTMLDivElement>(null);

  // Show the newest message by scrolling inside the conversation only, never the whole page.
  useEffect(() => {
    if (list.current) list.current.scrollTop = list.current.scrollHeight;
  }, [messages?.length]);

  async function submit(e: FormEvent) {
    e.preventDefault();
    if (!text.trim()) return;
    setBusy(true);
    setError(null);
    const err = await onSend(text.trim());
    setBusy(false);
    if (err) setError(err);
    else setText("");
  }

  return (
    <div className="thread">
      <div className="thread-list" role="log" aria-live="polite" ref={list}>
        {messages === null ? <p className="muted">Loading…</p> : messages.length === 0 ? (
          <p className="muted thread-empty">No messages yet.</p>
        ) : messages.map((m) => (
          <div key={m.id} className={`bubble ${m.sender === mine ? "bubble-mine" : "bubble-theirs"}`}>
            <p>{m.body}</p>
            <span>{m.sender === mine ? "You" : m.sender_name} · {when(m.created_at)}</span>
          </div>
        ))}
      </div>
      {note && <p className="muted small thread-note">{note}</p>}
      {disabled ? <p className="muted small">{disabled}</p> : (
        <form className="thread-form" onSubmit={submit}>
          <label className="sr-only" htmlFor="msg-box">Message</label>
          <textarea id="msg-box" rows={3} maxLength={2000} placeholder={placeholder} value={text}
                    onChange={(e) => setText(e.target.value)}
                    onKeyDown={(e) => { if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) void submit(e); }} />
          {error && <p className="error" role="alert">{error}</p>}
          <div className="actions"><button type="submit" disabled={busy || !text.trim()}>{busy ? "Sending…" : "Send"}</button></div>
        </form>
      )}
    </div>
  );
}
