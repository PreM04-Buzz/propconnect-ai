import { NavLink, Outlet } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";

const upcoming = [{ label: "Market trends", phase: 4 }];

export function AppLayout() {
  const { user, signOut } = useAuth();
  return (
    <div className="shell">
      <aside className="sidebar">
        <div className="brand">
          PropConnect <span>AI</span>
        </div>
        <nav>
          <NavLink to="/" end>Dashboard</NavLink>
          <NavLink to="/pipeline">Lead pipeline</NavLink>
          <NavLink to="/clients">Clients</NavLink>
          <NavLink to="/properties">Properties</NavLink>
          <NavLink to="/calendar">Calendar</NavLink>
          <NavLink to="/offers">Offers</NavLink>
          {user?.role === "admin" && <NavLink to="/team">Team</NavLink>}
          {upcoming.map((m) => (
            <span key={m.label} className="nav-soon" title="Coming in a later phase">
              {m.label} <small>Later</small>
            </span>
          ))}
        </nav>
        <div className="sidebar-user">
          <div>{user?.full_name}</div>
          <small>{user?.role === "admin" ? "Broker / admin" : "Agent"} · <NavLink to="/account" className="quiet-link">Account</NavLink></small>
          <button className="link-button" onClick={signOut}>Sign out</button>
        </div>
      </aside>
      <main className="content">
        <Outlet />
      </main>
    </div>
  );
}
