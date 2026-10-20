import { api, errorMessage, type Offer, type OfferStatus } from "../api/client";
import { money } from "../lib/format";

/** The buttons that make sense for an offer's current status. */
export function OfferActions({ offer, onChanged, onError }: { offer: Offer; onChanged: () => void; onError: (m: string) => void }) {
  async function change(status: OfferStatus) {
    let counter_amount: number | undefined;
    let amount: number | undefined;
    if (status === "countered") {
      const v = window.prompt("What did the seller counter with? ($)", String(Math.round(offer.list_price ?? offer.amount)));
      if (!v) return;
      counter_amount = Number(v.replace(/[$,\s]/g, ""));
    }
    if (status === "submitted" && offer.status === "countered") {
      const v = window.prompt("Revised offer amount ($)", String(Math.round(offer.counter_amount ?? offer.amount)));
      if (!v) return;
      amount = Number(v.replace(/[$,\s]/g, ""));
    }
    if (status === "accepted" &&
        !window.confirm(`Accept ${money(offer.amount)} for ${offer.property_address}? The lead moves to Won and the home is marked sold.`)) return;
    const { error } = await api.POST("/api/offers/{offer_id}/status", {
      params: { path: { offer_id: offer.id } }, body: { status, counter_amount, amount },
    });
    if (error) onError(errorMessage(error));
    onChanged();
  }

  const s = offer.status;
  return (
    <span className="offer-actions">
      {s === "draft" && <button className="link-button" onClick={() => change("submitted")}>Submit</button>}
      {s === "countered" && <button className="link-button" onClick={() => change("submitted")}>Send revised offer</button>}
      {s === "submitted" && <button className="link-button" onClick={() => change("countered")}>Seller countered</button>}
      {(s === "submitted" || s === "countered") && <>
        <button className="link-button" onClick={() => change("accepted")}>Accepted</button>
        <button className="link-button" onClick={() => change("rejected")}>Rejected</button>
      </>}
      {(s === "draft" || s === "submitted" || s === "countered") &&
        <button className="link-button" onClick={() => change("withdrawn")}>Withdraw</button>}
    </span>
  );
}
