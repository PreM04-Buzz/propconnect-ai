import { useEffect, useState, type FormEvent } from "react";
import { api, errorMessage, type AppointmentType, type ClientDetail, type ClientListItem } from "../api/client";
import { isoDate, money } from "../lib/format";

interface Props {
  clientId?: number; // preselect when opened from a lead or client page
  onSaved: () => void;
  onCancel: () => void;
}

const DURATIONS = [30, 45, 60, 90];

export function ScheduleForm({ clientId, onSaved, onCancel }: Props) {
  const [clients, setClients] = useState<ClientListItem[]>([]);
  const [client, setClient] = useState<ClientDetail | null>(null);
  const tomorrow = new Date(Date.now() + 86_400_000);
  const [v, setV] = useState({
    client: clientId ? String(clientId) : "", type: "viewing" as AppointmentType, property: "",
    date: isoDate(tomorrow), time: "10:00", minutes: "60", notes: "",
  });
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    api.GET("/api/clients").then(({ data }) => data && setClients(data));
  }, []);

  useEffect(() => {
    if (!v.client) return setClient(null);
    api.GET("/api/clients/{client_id}", { params: { path: { client_id: Number(v.client) } } }).then(({ data }) => {
      setClient(data ?? null);
      const first = data?.interests[0]?.property_id;
      setV((prev) => ({ ...prev, property: first ? String(first) : "" }));
    });
  }, [v.client]);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    const start = new Date(`${v.date}T${v.time}`);
    const end = new Date(start.getTime() + Number(v.minutes) * 60_000);
    setSaving(true);
    const { error } = await api.POST("/api/appointments", { body: {
      client_id: Number(v.client), appointment_type: v.type, property_id: v.property ? Number(v.property) : null,
      starts_at: start.toISOString(), ends_at: end.toISOString(), notes: v.notes.trim() || null,
    } });
    setSaving(false);
    if (error) return setError(errorMessage(error));
    onSaved();
  }

  return (
    <form className="card schedule-form" onSubmit={submit}>
      <h2>Schedule an appointment</h2>
      <div className="form-grid">
        <label>Client
          <select required value={v.client} onChange={(e) => setV({ ...v, client: e.target.value })}>
            <option value="">Choose a client…</option>
            {clients.map((c) => <option key={c.id} value={c.id}>{c.first_name} {c.last_name}</option>)}
          </select>
        </label>
        <label>Type
          <select value={v.type} onChange={(e) => setV({ ...v, type: e.target.value as AppointmentType })}>
            <option value="viewing">Viewing</option><option value="meeting">Meeting</option><option value="follow_up">Follow-up</option>
          </select>
        </label>
        <label className="wide">Property {v.type === "viewing" ? "" : "(optional)"}
          <select value={v.property} onChange={(e) => setV({ ...v, property: e.target.value })} required={v.type === "viewing"}>
            <option value="">{client && client.interests.length === 0 ? "Nothing shortlisted yet" : "No property"}</option>
            {client?.interests.map((i) => (
              <option key={i.property_id} value={i.property_id}>
                {i.property.street_address}, {i.property.city} · {money(i.property.price)}
              </option>
            ))}
          </select>
        </label>
        <label>Date<input type="date" required value={v.date} onChange={(e) => setV({ ...v, date: e.target.value })} /></label>
        <label>Start<input type="time" required step={900} value={v.time} onChange={(e) => setV({ ...v, time: e.target.value })} /></label>
        <label>Length
          <select value={v.minutes} onChange={(e) => setV({ ...v, minutes: e.target.value })}>
            {DURATIONS.map((m) => <option key={m} value={m}>{m} minutes</option>)}
          </select>
        </label>
        <label className="wide">Notes<input value={v.notes} onChange={(e) => setV({ ...v, notes: e.target.value })} placeholder="e.g. Bring the HOA documents" /></label>
      </div>
      {error && <p className="error" role="alert">{error}</p>}
      <div className="actions">
        <button type="submit" disabled={saving}>{saving ? "Saving…" : "Schedule"}</button>
        <button type="button" className="secondary" onClick={onCancel}>Cancel</button>
      </div>
    </form>
  );
}
