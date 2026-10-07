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
