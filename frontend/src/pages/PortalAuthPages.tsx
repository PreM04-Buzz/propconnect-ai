import { useEffect, useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { clientTokenStore, errorMessage, portalApi } from "../api/client";
import { LoginArt } from "../components/LoginArt";

function Shell({ line, children }: { line: string; children: React.ReactNode }) {
  return (
    <div className="login">
      <aside className="login-art">
        <LoginArt />
        <div className="login-art-copy">
          <p className="login-art-brand">PropConnect <span>AI</span></p>
          <p className="login-art-line">{line}</p>
        </div>
      </aside>
      <main className="login-main">
        <div className="login-watermark" aria-hidden="true" />
        {children}
      </main>
    </div>
  );
}

/** Clients sign in to their portal (staff use the normal sign-in page). */
export function PortalLoginPage() {
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (clientTokenStore.get()) navigate("/portal", { replace: true });
  }, [navigate]);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      const { data, error: err } = await portalApi.POST("/api/portal/login", { body: { email: email.trim(), password } });
      if (err || !data) return setError(errorMessage(err, "That email and password don’t match."));
      clientTokenStore.set(data.access_token);
      navigate("/portal", { replace: true });
    } catch {
      setError("Can’t reach the server right now. It may be waking up: try again in a minute.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Shell line="Follow your home search and message your agent, any time.">
      <form className="login-card" onSubmit={submit}>
        <h1>Client sign-in</h1>
        <p>Use the email your agent has and the password you chose from your invitation.</p>
        <label>Email<input type="email" required autoComplete="email" value={email} onChange={(e) => setEmail(e.target.value)} /></label>
        <label>Password<input type="password" required autoComplete="current-password" value={password}
                              onChange={(e) => setPassword(e.target.value)} /></label>
        {error && <p className="error" role="alert">{error}</p>}
        <button type="submit" disabled={busy || !email || !password}>{busy ? "Signing in…" : "Sign in"}</button>
        <p className="muted small">No password yet? Ask your agent to send you an invitation. Forgot it? They can send a new link.</p>
      </form>
      <p className="login-switch">Agent or broker? <Link to="/login">Staff sign-in</Link> · <Link to="/welcome">About PropConnect AI</Link></p>
    </Shell>
  );
}

/** The invitation link lands here: the client chooses a password. */
export function PortalSetupPage() {
  const navigate = useNavigate();
  const [token] = useState(() => new URLSearchParams(window.location.hash.replace(/^#/, "")).get("token") ?? "");
  const [password, setPassword] = useState("");
  const [again, setAgain] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    // Take the token out of the address bar so it isn't left in history or shared by accident.
    if (window.location.hash) window.history.replaceState(null, "", window.location.pathname);
  }, []);

  async function submit(e: FormEvent) {
    e.preventDefault();
    if (password !== again) return setError("The two passwords don’t match.");
    setError(null);
    setBusy(true);
    try {
      const { data, error: err } = await portalApi.POST("/api/portal/accept", { body: { token, password } });
      if (err || !data) return setError(errorMessage(err));
      clientTokenStore.set(data.access_token);
      navigate("/portal", { replace: true });
    } catch {
      setError("Can’t reach the server right now. It may be waking up: try again in a minute.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Shell line="Welcome! Choose a password and you’re in.">
      {!token ? (
        <div className="login-card">
          <h1>This link isn’t complete</h1>
          <p>Open the link from your invitation email again, or ask your agent to send a new one.</p>
          <p className="muted small">Already set a password? <Link to="/portal/login">Sign in here</Link>.</p>
        </div>
      ) : (
        <form className="login-card" onSubmit={submit}>
          <h1>Set your password</h1>
          <p>You’ll use it with your email address to sign in to your client portal.</p>
          <label>Password<input type="password" required minLength={8} autoComplete="new-password" placeholder="8+ characters"
                                value={password} onChange={(e) => setPassword(e.target.value)} /></label>
          <label>Password again<input type="password" required minLength={8} autoComplete="new-password"
                                      value={again} onChange={(e) => setAgain(e.target.value)} /></label>
          {error && <p className="error" role="alert">{error}</p>}
          <button type="submit" disabled={busy || password.length < 8 || !again}>{busy ? "Saving…" : "Save and continue"}</button>
        </form>
      )}
    </Shell>
  );
}
