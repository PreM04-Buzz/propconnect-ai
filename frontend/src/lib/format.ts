import type { FinancingStatus, LeadStage } from "../api/client";

export const STAGES: LeadStage[] = ["new", "contacted", "qualified", "proposal", "negotiation", "won", "lost"];

export const stageLabel = (s: LeadStage) => s.charAt(0).toUpperCase() + s.slice(1);

const money0 = new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 });
export const money = (v?: number | null) => (v == null ? "—" : money0.format(v));
export const compactMoney = (v?: number | null) =>
  v == null ? "—" : v >= 1_000_000 ? `$${(v / 1_000_000).toFixed(v >= 10_000_000 ? 0 : 1)}M` : `$${Math.round(v / 1000)}K`;

export const financingLabel: Record<FinancingStatus, string> = {
  unknown: "Unknown",
  not_started: "Not started",
  pre_qualified: "Pre-qualified",
  pre_approved: "Pre-approved",
  cash: "Cash buyer",
};

export function shortDate(iso?: string | null) {
  if (!iso) return "—";
  return new Date(iso).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
}

export function relativeDays(iso?: string | null) {
  if (!iso) return "No contact yet";
  const days = Math.floor((Date.now() - new Date(iso).getTime()) / 86_400_000);
  if (days <= 0) return "Today";
  if (days === 1) return "Yesterday";
  return `${days} days ago`;
}

/** Turns "" into undefined and numeric strings into numbers for form submission. */
export const num = (v: string) => (v.trim() === "" ? null : Number(v));
export const str = (v: string) => (v.trim() === "" ? null : v.trim());

// ---- Dates and times for the calendar ----

/** Monday 00:00 (local time) of the week containing `d`. */
export function startOfWeek(d: Date): Date {
  const x = new Date(d.getFullYear(), d.getMonth(), d.getDate());
  const day = (x.getDay() + 6) % 7; // Monday = 0
  x.setDate(x.getDate() - day);
  return x;
}

export function addDays(d: Date, n: number): Date {
  const x = new Date(d);
  x.setDate(x.getDate() + n);
  return x;
}

export const sameDay = (a: Date, b: Date) =>
  a.getFullYear() === b.getFullYear() && a.getMonth() === b.getMonth() && a.getDate() === b.getDate();

export const timeOf = (iso: string) =>
  new Date(iso).toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit" });

export const dayLabel = (d: Date) => d.toLocaleDateString("en-US", { weekday: "short", month: "short", day: "numeric" });

export const dateTime = (iso?: string | null) =>
  iso ? new Date(iso).toLocaleString("en-US", { weekday: "short", month: "short", day: "numeric", hour: "numeric", minute: "2-digit" }) : "—";

/** "2026-10-24" for an <input type="date">, in local time. */
export const isoDate = (d: Date) =>
  `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;

export const typeLabel: Record<string, string> = { viewing: "Viewing", meeting: "Meeting", follow_up: "Follow-up" };

export const offerStatusLabel: Record<string, string> = {
  draft: "Draft", submitted: "Submitted", countered: "Countered", accepted: "Accepted", rejected: "Rejected", withdrawn: "Withdrawn",
};
