import { useEffect, useRef, useState, type ReactNode } from "react";

/** Plays its animation only while visible, so off-screen scenes don't run. */
export function InView({ className, label, children }: { className: string; label: string; children: ReactNode }) {
  const ref = useRef<HTMLDivElement>(null);
  const [on, setOn] = useState(false);
  useEffect(() => {
    const el = ref.current;
    if (!el || typeof IntersectionObserver === "undefined") return setOn(true);
    const io = new IntersectionObserver((entries) => setOn(Boolean(entries[0]?.isIntersecting)), { threshold: 0.35 });
    io.observe(el);
    return () => io.disconnect();
  }, []);
  return <div ref={ref} className={`wa-scene ${className} ${on ? "wa-play" : ""}`} role="img" aria-label={label}>{children}</div>;
}

/** A client fills in the request form, sends it, and it reaches their agent. */
export function ClientFlowArt() {
  return (
    <InView className="wa-client" label="A client fills in a short form, sends it, and it reaches their agent">
      <div className="wa-form">
        <p className="wa-form-title">Find your next home</p>
        {["Chicago, 2+ bedrooms", "Up to $400,000", "Pre-approved, moving in 3 months"].map((t, i) => (
          <div key={t} className={`wa-field wa-field-${i + 1}`}><span>{t}</span></div>
        ))}
        <div className="wa-send">Send my request</div>
      </div>
      <div className="wa-note">Request</div>
      <div className="wa-agent">
        <div className="wa-avatar">M</div>
        <p><b>Maria</b><br />your agent</p>
      </div>
    </InView>
  );
}

const STAGES = ["New", "Contacted", "Viewing", "Offer", "Won"];

/** A lead moves through the pipeline while the AI suggests the next step. */
export function PipelineArt() {
  return (
    <InView className="wa-pipe" label="A lead moves from New to Won while the AI suggests the next step">
      <div className="wa-cols">
        {STAGES.map((s) => <div key={s} className="wa-col"><span>{s}</span></div>)}
      </div>
      <div className="wa-card"><b>Aisha P.</b><span>Score 80</span></div>
      <div className="wa-bubble"><b>AI next step</b> Schedule viewings for her two shortlisted homes</div>
      <div className="wa-sold">SOLD</div>
    </InView>
  );
}

/** New requests arrive and the broker assigns each to an agent. */
export function BrokerArt() {
  const agents = ["Maria", "James", "Priya"];
  return (
    <InView className="wa-broker" label="New client requests arrive and the broker assigns each one to an agent">
      <div className="wa-inbox">
        <p>New requests</p>
        {["Dana B.", "Marcus R.", "Lena O."].map((n, i) => <div key={n} className={`wa-req wa-req-${i + 1}`}>{n}</div>)}
      </div>
      <div className="wa-lanes">
        {agents.map((a, i) => (
          <div key={a} className="wa-lane">
            <div className="wa-avatar small">{a[0]}</div>
            <span>{a}</span>
            <div className={`wa-slot wa-slot-${i + 1}`} />
          </div>
        ))}
      </div>
    </InView>
  );
}
