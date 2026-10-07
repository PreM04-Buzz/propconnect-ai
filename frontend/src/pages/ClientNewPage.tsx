import { useNavigate } from "react-router-dom";
import { api, errorMessage } from "../api/client";
import { ClientForm } from "../components/ClientForm";

export function ClientNewPage() {
  const navigate = useNavigate();
  return (
    <section className="narrow">
      <h1>Add a client</h1>
      <p className="muted">A new lead is opened in the New stage automatically.</p>
      <ClientForm
        submitLabel="Save client"
        onCancel={() => navigate("/clients")}
        onSubmit={async (body) => {
          const { data, error } = await api.POST("/api/clients", { body: { ...body, create_lead: true } });
          if (data) {
            navigate(`/clients/${data.id}`);
            return null;
          }
          return errorMessage(error);
        }}
      />
    </section>
  );
}
