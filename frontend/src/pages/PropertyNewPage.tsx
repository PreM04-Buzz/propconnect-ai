import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { api, errorMessage } from "../api/client";
import { num, str } from "../lib/format";

export function PropertyNewPage() {
  const navigate = useNavigate();
  const [v, setV] = useState({ street_address: "", city: "", zip_code: "", price: "", bedrooms: "", bathrooms: "", house_size_sqft: "" });
  const [error, setError] = useState<string | null>(null);
  const set = (k: keyof typeof v) => (e: { target: { value: string } }) => setV({ ...v, [k]: e.target.value });

  async function submit(e: FormEvent) {
    e.preventDefault();
    const { data, error } = await api.POST("/api/properties", { body: {
      status: "for_sale", street_address: str(v.street_address), city: v.city.trim(), state: "Illinois", zip_code: v.zip_code.trim(),
      price: num(v.price), bedrooms: num(v.bedrooms), bathrooms: num(v.bathrooms), house_size_sqft: num(v.house_size_sqft),
    } });
    if (data) navigate(`/properties/${data.id}`);
    else setError(errorMessage(error));
  }

  return (
    <section className="narrow">
      <h1>Add a listing</h1>
      <form className="form" onSubmit={submit}>
        <fieldset>
          <legend>Address</legend>
          <label className="wide">Street address<input required value={v.street_address} onChange={set("street_address")} /></label>
          <label>City<input required value={v.city} onChange={set("city")} /></label>
          <label>ZIP<input required pattern="\d{5}" maxLength={5} value={v.zip_code} onChange={set("zip_code")} /></label>
        </fieldset>
        <fieldset>
          <legend>Home</legend>
          <label>Price ($)<input required type="number" min={0} step={1000} value={v.price} onChange={set("price")} /></label>
          <label>Bedrooms<input type="number" min={0} value={v.bedrooms} onChange={set("bedrooms")} /></label>
          <label>Bathrooms<input type="number" min={0} step={0.5} value={v.bathrooms} onChange={set("bathrooms")} /></label>
          <label>Size (sq ft)<input type="number" min={0} value={v.house_size_sqft} onChange={set("house_size_sqft")} /></label>
        </fieldset>
        {error && <p className="error">{error}</p>}
        <div className="actions">
          <button type="submit">Save listing</button>
          <button type="button" className="secondary" onClick={() => navigate("/properties")}>Cancel</button>
        </div>
      </form>
    </section>
  );
}
