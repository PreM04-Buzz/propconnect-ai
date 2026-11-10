import { useState, type FormEvent } from "react";
import { Link, Navigate, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { LoginArt } from "../components/LoginArt";

export function LoginPage() {
  const { user, signIn } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const from = (location.state as { from?: string } | null)?.from ?? "/";

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [slow, setSlow] = useState(false);

  if (user) return <Navigate to={from} replace />;

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    // The free server sleeps when nobody uses it and takes up to a minute to wake.
    const timer = setTimeout(() => setSlow(true), 4000);
    try {
      await signIn(email, password);
      navigate(from, { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Sign-in failed.");
    } finally {
      clearTimeout(timer);
      setSlow(false);
      setSubmitting(false);
    }
  }

  return (
    <div className="login">
      <aside className="login-art">
        <LoginArt />
        <div className="login-art-copy">
          <p className="login-art-brand">PropConnect <span>AI</span></p>
          <p className="login-art-line">Every client, viewing and offer in one place, with a next step suggested for each lead.</p>
        </div>
      </aside>
      <main className="login-main">
      <div className="login-watermark" aria-hidden="true" />
      <form className="login-card" onSubmit={handleSubmit} noValidate>
        <h1>Sign in</h1>
        <p className="muted">Use the email and password your broker gave you.</p>
        <label>
          Email
          <input type="email" autoComplete="username" required value={email}
                 onChange={(e) => setEmail(e.target.value)} />
        </label>
        <label>
          Password
          <input type="password" autoComplete="current-password" required value={password}
                 onChange={(e) => setPassword(e.target.value)} />
        </label>
        {error && <p className="error" role="alert">{error}</p>}
        {slow && <p className="notice" role="status">Waking up the server. The first sign-in after a quiet spell can take up to a minute.</p>}
        <button type="submit" disabled={submitting || !email || !password}>
          {submitting ? "Signing in…" : "Sign in"}
        </button>
      </form>
      <p className="login-switch">Looking to buy or sell? <Link to="/start">Tell us what you need</Link> · <Link to="/welcome">About PropConnect AI</Link></p>
      </main>
    </div>
  );
}
