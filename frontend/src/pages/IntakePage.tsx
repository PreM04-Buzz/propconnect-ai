import { useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { api, errorMessage, type IntakeForm } from "../api/client";
import { LoginArt } from "../components/LoginArt";

const EMPTY = {
  first_name: "", last_name: "", email: "", phone: "", client_type: "buyer", preferred_city: "",
  budget_min: "", budget_max: "", min_bedrooms: "", min_bathrooms: "", financing_status: "unknown",
  purchase_timeline_months: "", notes: "", consent: false, website: "",
};

const num = (v: string) => (v.trim() === "" ? null : Number(v.replace(/[$,\s]/g, "")));

/** Public page: a client tells us what they're looking for. No account needed. */
export function IntakePage() {
  const [v, setV] = useState(EMPTY);
  const [error, setError] = useState<string | null>(null);
  const [sent, setSent] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const set = (k: keyof typeof EMPTY) => (e: { target: { value: string } }) => setV({ ...v, [k]: e.target.value });
  const selling = v.client_type === "seller";

  async function submit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSaving(true);
    const body = {
      first_name: v.first_name, last_name: v.last_name, email: v.email, phone: v.phone || null,
      client_type: v.client_type as IntakeForm["client_type"], preferred_city: v.preferred_city || null,
      budget_min: num(v.budget_min), budget_max: num(v.budget_max),
      min_bedrooms: num(v.min_bedrooms), min_bathrooms: num(v.min_bathrooms),
      financing_status: v.financing_status as IntakeForm["financing_status"],
      purchase_timeline_months: num(v.purchase_timeline_months), notes: v.notes || null,
      preferred_state: "Illinois", consent: v.consent, website: v.website || null,
    };
    let result;
    try {
      result = await api.POST("/api/public/intake", { body });
    } catch {
      setSaving(false);
      return setError("Can’t reach the server right now. Please try again in a moment.");
    }
    setSaving(false);
    if (result.error) return setError(errorMessage(result.error, "Something went wrong. Please check the form and try again."));
    setSent(result.data?.message ?? "Thank you! An agent will be in touch soon.");
    setV(EMPTY);
  }

  return (
    <div className="login">
      <aside className="login-art">
        <LoginArt />
        <div className="login-art-copy">
          <p className="login-art-brand">PropConnect <span>AI</span></p>
          <p className="login-art-line">Tell us what you’re looking for, and one of our agents will take it from there.</p>
        </div>
      </aside>
      <main className="login-main intake-main">
        <div className="login-watermark" aria-hidden="true" />
        {sent ? (
          <div className="login-card intake-card" role="status">
            <h1>Thank you</h1>
            <p>{sent}</p>
            <p className="muted">There’s nothing else you need to do. Keep an eye on your email and phone.</p>
            <div className="actions"><button type="button" className="secondary" onClick={() => setSent(null)}>Send another request</button></div>
          </div>
        ) : (
          <form className="login-card intake-card" onSubmit={submit}>
            <h1>Find your next home</h1>
            <p className="muted">It takes about two minutes. Only what you tell us here is shared with your agent.</p>

            <fieldset className="intake-group">
              <legend>About you</legend>
              <div className="form-grid">
                <label>First name<input required maxLength={80} autoComplete="given-name" value={v.first_name} onChange={set("first_name")} /></label>
                <label>Last name<input required maxLength={80} autoComplete="family-name" value={v.last_name} onChange={set("last_name")} /></label>
                <label>Email<input required type="email" autoComplete="email" value={v.email} onChange={set("email")} /></label>
                <label>Phone (optional)<input type="tel" maxLength={30} autoComplete="tel" value={v.phone} onChange={set("phone")} /></label>
              </div>
            </fieldset>

            <fieldset className="intake-group">
              <legend>What you’re looking for</legend>
              <div className="form-grid">
                <label>I want to
                  <select value={v.client_type} onChange={set("client_type")}>
                    <option value="buyer">Buy a home</option><option value="seller">Sell my home</option><option value="both">Buy and sell</option>
                  </select>
                </label>
                <label>{selling ? "Where is your home?" : "Where would you like to live?"}
                  <input maxLength={100} placeholder="e.g. Chicago" value={v.preferred_city} onChange={set("preferred_city")} />
                </label>
                {!selling && <>
                  <label>Budget from ($)<input inputMode="numeric" placeholder="e.g. 250,000" value={v.budget_min} onChange={set("budget_min")} /></label>
                  <label>Budget up to ($)<input inputMode="numeric" placeholder="e.g. 400,000" value={v.budget_max} onChange={set("budget_max")} /></label>
                  <label>Bedrooms, at least
                    <select value={v.min_bedrooms} onChange={set("min_bedrooms")}>
                      <option value="">No preference</option>{[1, 2, 3, 4, 5].map((n) => <option key={n} value={n}>{n}+</option>)}
                    </select>
                  </label>
                  <label>Bathrooms, at least
                    <select value={v.min_bathrooms} onChange={set("min_bathrooms")}>
                      <option value="">No preference</option>{[1, 1.5, 2, 3].map((n) => <option key={n} value={n}>{n}+</option>)}
                    </select>
                  </label>
                </>}
              </div>
            </fieldset>

            <fieldset className="intake-group">
              <legend>Timing{selling ? "" : " and financing"}</legend>
              <div className="form-grid">
                <label>When would you like to {selling ? "sell" : "move"}?
                  <select value={v.purchase_timeline_months} onChange={set("purchase_timeline_months")}>
                    <option value="">Not sure yet</option><option value="1">Within a month</option><option value="3">In 1–3 months</option>
                    <option value="6">In 3–6 months</option><option value="12">In 6–12 months</option><option value="18">More than a year</option>
                  </select>
                </label>
                {!selling && (
                  <label>How will you pay?
                    <select value={v.financing_status} onChange={set("financing_status")}>
                      <option value="unknown">Not sure yet</option><option value="not_started">Mortgage, haven’t started</option>
                      <option value="pre_qualified">Mortgage, pre-qualified</option><option value="pre_approved">Mortgage, pre-approved</option>
                      <option value="cash">Cash</option>
                    </select>
                  </label>
                )}
                <label className="wide">Anything else we should know? (optional)
                  <textarea rows={3} maxLength={1000} placeholder="e.g. near good schools, a yard for the dog, close to the Blue Line"
                            value={v.notes} onChange={set("notes")} />
                </label>
              </div>
            </fieldset>

            {/* Hidden from people; bots tend to fill it in. */}
            <label className="intake-hp" aria-hidden="true">Website<input tabIndex={-1} autoComplete="off" value={v.website} onChange={set("website")} /></label>

            <label className="intake-consent">
              <input type="checkbox" checked={v.consent} onChange={(e) => setV({ ...v, consent: e.target.checked })} required />
              <span>I agree that a PropConnect agent may contact me about this request by email or phone.</span>
            </label>
            {error && <p className="error" role="alert">{error}</p>}
            <button type="submit" disabled={saving || !v.consent}>{saving ? "Sending…" : "Send my request"}</button>
            <p className="muted small"><Link to="/welcome">About PropConnect AI</Link> · Agents and brokers: <Link to="/login">sign in here</Link>.</p>
          </form>
        )}
      </main>
    </div>
  );
}
