import { Navigate, Route, Routes } from "react-router-dom";
import { ProtectedRoute } from "./auth/ProtectedRoute";
import { AppLayout } from "./components/AppLayout";
import { AccountPage } from "./pages/AccountPage";
import { CalendarPage } from "./pages/CalendarPage";
import { OffersPage } from "./pages/OffersPage";
import { ClientDetailPage } from "./pages/ClientDetailPage";
import { ClientNewPage } from "./pages/ClientNewPage";
import { ClientsPage } from "./pages/ClientsPage";
import { DashboardPage } from "./pages/DashboardPage";
import { LeadDetailPage } from "./pages/LeadDetailPage";
import { LoginPage } from "./pages/LoginPage";
import { PipelinePage } from "./pages/PipelinePage";
import { PropertiesPage } from "./pages/PropertiesPage";
import { PropertyDetailPage } from "./pages/PropertyDetailPage";
import { PropertyNewPage } from "./pages/PropertyNewPage";
import { AdminPage } from "./pages/AdminPage";
import { IntakePage } from "./pages/IntakePage";
import { WelcomePage } from "./pages/WelcomePage";

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/start" element={<IntakePage />} />
      <Route path="/welcome" element={<WelcomePage />} />
      <Route element={<ProtectedRoute><AppLayout /></ProtectedRoute>}>
        <Route index element={<DashboardPage />} />
        <Route path="pipeline" element={<PipelinePage />} />
        <Route path="leads/:id" element={<LeadDetailPage />} />
        <Route path="clients" element={<ClientsPage />} />
        <Route path="clients/new" element={<ClientNewPage />} />
        <Route path="clients/:id" element={<ClientDetailPage />} />
        <Route path="properties" element={<PropertiesPage />} />
        <Route path="properties/new" element={<PropertyNewPage />} />
        <Route path="properties/:id" element={<PropertyDetailPage />} />
        <Route path="calendar" element={<CalendarPage />} />
        <Route path="offers" element={<OffersPage />} />
        <Route path="account" element={<AccountPage />} />
        <Route path="admin" element={<ProtectedRoute roles={["admin"]}><AdminPage /></ProtectedRoute>} />
        <Route path="team" element={<Navigate to="/admin?tab=team" replace />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
