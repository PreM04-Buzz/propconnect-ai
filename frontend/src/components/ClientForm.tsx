import { useState, type FormEvent } from "react";
import type { ClientCreate, ClientDetail, ClientType, FinancingStatus } from "../api/client";
import { financingLabel, num, str } from "../lib/format";

type Values = Record<string, string | boolean>;

function initial(c?: ClientDetail): Values {
  const s = (v: unknown) => (v == null ? "" : String(v));
  return {
    first_name: s(c?.first_name), last_name: s(c?.last_name), email: s(c?.email), phone: s(c?.phone),
    client_type: c?.client_type ?? "buyer", budget_min: s(c?.budget_min), budget_max: s(c?.budget_max),
    budget_confirmed: c?.budget_confirmed ?? false, preferred_city: s(c?.preferred_city),
    preferred_zip: s(c?.preferred_zip), min_bedrooms: s(c?.min_bedrooms), min_bathrooms: s(c?.min_bathrooms),
    min_house_size_sqft: s(c?.min_house_size_sqft), financing_status: c?.financing_status ?? "unknown",
    purchase_timeline_months: s(c?.purchase_timeline_months), notes: s(c?.notes), lead_source: "",
  };
}

interface Props {
  client?: ClientDetail;
  submitLabel: string;
  onSubmit: (body: ClientCreate) => Promise<string | null>; // returns an error message or null
  onCancel?: () => void;
}

export function ClientForm({ client, submitLabel, onSubmit, onCancel }: Props) {
  const [v, setV] = useState<Values>(() => initial(client));
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const set = (k: string) => (e: { target: { value: string } }) => setV({ ...v, [k]: e.target.value });
  const t = (k: string) => String(v[k] ?? "");

  async function submit(e: FormEvent) {
    e.preventDefault();
    setSaving(true);
    const body: ClientCreate = {
      first_name: t("first_name").trim(), last_name: t("last_name").trim(), email: str(t("email")),
      phone: str(t("phone")), client_type: t("client_type") as ClientType, budget_min: num(t("budget_min")),
      budget_max: num(t("budget_max")), budget_confirmed: Boolean(v.budget_confirmed),
      preferred_city: str(t("preferred_city")), preferred_state: "Illinois", preferred_zip: str(t("preferred_zip")),
      min_bedrooms: num(t("min_bedrooms")), min_bathrooms: num(t("min_bathrooms")),
      min_house_size_sqft: num(t("min_house_size_sqft")), financing_status: t("financing_status") as FinancingStatus,
      purchase_timeline_months: num(t("purchase_timeline_months")), notes: str(t("notes")),
      lead_source: str(t("lead_source")), create_lead: true,
    };
    setError(await onSubmit(body));
    setSaving(false);
  }

  return (
    <form className="form" onSubmit={submit}>
      <fieldset>
        <legend>Contact</legend>
        <label>First name<input required value={t("first_name")} onChange={set("first_name")} /></label>
        <label>Last name<input required value={t("last_name")} onChange={set("last_name")} /></label>
        <label>Email<input type="email" value={t("email")} onChange={set("email")} /></label>
        <label>Phone<input value={t("phone")} onChange={set("phone")} /></label>
        <label>Client type
          <select value={t("client_type")} onChange={set("client_type")}>
            <option value="buyer">Buyer</option><option value="seller">Seller</option><option value="both">Buyer and seller</option>
          </select>
        </label>
        {!client && (
          <label>Lead source
            <select value={t("lead_source")} onChange={set("lead_source")}>
              <option value="">Not specified</option>
              {["Website", "Referral", "Open house", "Zillow inquiry", "Social media", "Walk-in"].map((s) => <option key={s}>{s}</option>)}
            </select>
          </label>
        )}
      </fieldset>
      <fieldset>
        <legend>What they're looking for</legend>
        <label>Budget from ($)<input type="number" min={0} step={5000} value={t("budget_min")} onChange={set("budget_min")} /></label>
        <label>Budget up to ($)<input type="number" min={0} step={5000} value={t("budget_max")} onChange={set("budget_max")} /></label>
        <label>Preferred city<input value={t("preferred_city")} onChange={set("preferred_city")} placeholder="e.g. Naperville" /></label>
        <label>Preferred ZIP<input value={t("preferred_zip")} onChange={set("preferred_zip")} pattern="\d{5}" maxLength={5} /></label>
        <label>Bedrooms (min)<input type="number" min={0} value={t("min_bedrooms")} onChange={set("min_bedrooms")} /></label>
        <label>Bathrooms (min)<input type="number" min={0} step={0.5} value={t("min_bathrooms")} onChange={set("min_bathrooms")} /></label>
        <label>Size (min sq ft)<input type="number" min={0} step={50} value={t("min_house_size_sqft")} onChange={set("min_house_size_sqft")} /></label>
      </fieldset>
      <fieldset>
        <legend>Readiness</legend>
        <label>Financing
          <select value={t("financing_status")} onChange={set("financing_status")}>
            {Object.entries(financingLabel).map(([k, label]) => <option key={k} value={k}>{label}</option>)}
          </select>
        </label>
        <label>Plans to buy within (months)<input type="number" min={0} value={t("purchase_timeline_months")} onChange={set("purchase_timeline_months")} /></label>
        <label className="check">
          <input type="checkbox" checked={Boolean(v.budget_confirmed)} onChange={(e) => setV({ ...v, budget_confirmed: e.target.checked })} />
          Budget confirmed with the client
        </label>
        <label className="wide">Notes<textarea rows={3} value={t("notes")} onChange={set("notes")} /></label>
      </fieldset>
      {error && <p className="error" role="alert">{error}</p>}
      <div className="actions">
        <button type="submit" disabled={saving}>{saving ? "Saving…" : submitLabel}</button>
        {onCancel && <button type="button" className="secondary" onClick={onCancel}>Cancel</button>}
      </div>
    </form>
  );
}
