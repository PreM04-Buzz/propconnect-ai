import { NavLink, Outlet } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";

// Modules arrive phase by phase; upcoming ones show which phase unlocks them.
const upcoming = [
  { label: "Clients & leads", phase: 2 },
  { label: "Properties", phase: 2 },
  { label: "Calendar", phase: 3 },
  { label: "Offers", phase: 3 },
  { label: "AI assistant", phase: 5 },
  { label: "Analytics", phase: 6 },
];

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
          {user?.role === "admin" && <NavLink to="/team">Team</NavLink>}
          {upcoming.map((m) => (
            <span key={m.label} className="nav-soon" title={`Available in phase ${m.phase}`}>
              {m.label} <small>Phase {m.phase}</small>
            </span>
          ))}
        </nav>
        <div className="sidebar-user">
          <div>{user?.full_name}</div>
          <small>{user?.role === "admin" ? "Broker / admin" : "Agent"}</small>
          <button className="link-button" onClick={signOut}>Sign out</button>
        </div>
      </aside>
      <main className="content">
        <Outlet />
      </main>
    </div>
  );
}
