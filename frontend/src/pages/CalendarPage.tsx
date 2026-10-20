import { useCallback, useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { api, errorMessage, type Appointment } from "../api/client";
import { ScheduleForm } from "../components/ScheduleForm";
import { addDays, dayLabel, isoDate, sameDay, startOfWeek, timeOf, typeLabel } from "../lib/format";

export function CalendarPage() {
  const [params, setParams] = useSearchParams();
  const prefillClient = params.get("client");
  const [weekStart, setWeekStart] = useState(() => startOfWeek(new Date()));
  const [items, setItems] = useState<Appointment[] | null>(null);
  const [showForm, setShowForm] = useState(Boolean(prefillClient));
  const [error, setError] = useState<string | null>(null);
  const days = Array.from({ length: 7 }, (_, i) => addDays(weekStart, i));

  const load = useCallback(async () => {
    const { data, error } = await api.GET("/api/appointments", {
      params: { query: { start: weekStart.toISOString(), end: addDays(weekStart, 7).toISOString() } },
    });
    if (data) setItems(data);
    else setError(errorMessage(error));
  }, [weekStart]);

  useEffect(() => {
    void load();
  }, [load]);

  async function setStatus(a: Appointment, status: "completed" | "cancelled" | "no_show") {
    let outcome: string | undefined;
    if (status === "completed" && a.appointment_type === "viewing") {
      outcome = window.prompt(`How did the viewing with ${a.client_name} go?`)?.trim();
      if (!outcome) return;
    }
    if (status === "cancelled" && !window.confirm(`Cancel this ${typeLabel[a.appointment_type]?.toLowerCase()}?`)) return;
    const { error } = await api.POST("/api/appointments/{appointment_id}/status", {
      params: { path: { appointment_id: a.id } }, body: { status, outcome },
    });
    if (error) setError(errorMessage(error));
    void load();
  }

  const scheduled = items?.filter((a) => a.status === "scheduled").length ?? 0;
  return (
    <section className="wide-page">
      <div className="page-head">
        <div>
          <h1>Calendar</h1>
          <p className="muted">
            {dayLabel(weekStart)} – {dayLabel(addDays(weekStart, 6))} · {scheduled} upcoming
          </p>
        </div>
        <div className="actions">
          <button className="secondary" onClick={() => setWeekStart(addDays(weekStart, -7))}>‹ Previous</button>
          <button className="secondary" onClick={() => setWeekStart(startOfWeek(new Date()))}>This week</button>
          <button className="secondary" onClick={() => setWeekStart(addDays(weekStart, 7))}>Next ›</button>
          <button onClick={() => setShowForm(true)}>Schedule</button>
        </div>
      </div>
      {showForm && (
        <ScheduleForm
          clientId={prefillClient ? Number(prefillClient) : undefined}
          onCancel={() => { setShowForm(false); setParams({}, { replace: true }); }}
          onSaved={() => { setShowForm(false); setParams({}, { replace: true }); void load(); }}
        />
      )}
      {error && <p className="error" role="alert">{error}</p>}
      <div className="week">
        {days.map((d) => {
          const today = sameDay(d, new Date());
          const list = (items ?? []).filter((a) => sameDay(new Date(a.starts_at), d));
          return (
            <div key={isoDate(d)} className={`day ${today ? "today" : ""}`}>
              <div className="day-head">{dayLabel(d)}{today && <span className="badge">Today</span>}</div>
              {list.map((a) => (
                <article key={a.id} className={`appt appt-${a.status}`}>
                  <div className="appt-time">{timeOf(a.starts_at)} – {timeOf(a.ends_at)}</div>
                  <div className="appt-title">
                    <span className={`badge type-${a.appointment_type}`}>{typeLabel[a.appointment_type]}</span>{" "}
                    {a.lead_id ? <Link to={`/leads/${a.lead_id}`}>{a.client_name}</Link> : a.client_name}
                  </div>
                  {a.property_address && <div className="muted small">{a.property_address}</div>}
                  {a.notes && <div className="muted small">{a.notes}</div>}
                  {a.status === "scheduled" ? (
                    <div className="appt-actions">
                      <button className="link-button" onClick={() => setStatus(a, "completed")}>Done</button>
                      <button className="link-button" onClick={() => setStatus(a, "no_show")}>No-show</button>
                      <button className="link-button" onClick={() => setStatus(a, "cancelled")}>Cancel</button>
                    </div>
                  ) : (
                    <div className="muted small cap">{a.status.replace("_", "-")}{a.outcome ? `: ${a.outcome}` : ""}</div>
                  )}
                </article>
              ))}
              {items && list.length === 0 && <p className="day-empty">Free</p>}
            </div>
          );
        })}
      </div>
      <p className="muted small">Double-booking is blocked: if a new appointment overlaps one you already have, you'll be told which one.</p>
    </section>
  );
}
