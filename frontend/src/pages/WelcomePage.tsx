import { Link } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { LoginArt } from "../components/LoginArt";
import { BrokerArt, ClientFlowArt, PipelineArt } from "../components/WelcomeArt";

/** The public front page: what PropConnect AI is, and the two ways in. */
export function WelcomePage() {
  const { user } = useAuth();
  const signIn = user
    ? <Link className="button wl-btn-ghost" to="/">Go to your dashboard</Link>
    : <Link className="button wl-btn-ghost" to="/login">Agent or broker? Sign in</Link>;

  return (
    <div className="wl">
      <header className="wl-nav">
        <Link to="/welcome" className="wl-brand">PropConnect <span>AI</span></Link>
        <nav>
          <Link to="/start">Find a home</Link>
          <Link to={user ? "/" : "/login"}>{user ? "Dashboard" : "Staff sign-in"}</Link>
          <Link to="/portal/login" className="wl-nav-client">Client sign-in</Link>
        </nav>
      </header>

      <section className="wl-hero">
        <div className="wl-hero-text">
          <p className="wl-kicker">Real estate CRM with an AI assistant</p>
          <h1>Every client, viewing and offer in one place, with a smart next step for each.</h1>
          <p className="wl-lead">
            PropConnect AI helps agents and brokers look after their clients, from the first hello to the day the
            keys change hands. Looking for a home? Tell us what you need in about two minutes.
          </p>
          <div className="wl-ctas">
            <Link className="button wl-btn-primary" to="/start">Find a home</Link>
            {signIn}
          </div>
        </div>
        <div className="wl-hero-art"><LoginArt /></div>
      </section>

      <section className="wl-how">
        <h2>How it works</h2>
        <ol className="wl-steps">
          <li><span>1</span><h3>Tell us what you need</h3><p>Where, your budget, how many bedrooms and when you’d like to move. No account needed.</p></li>
          <li><span>2</span><h3>We match you with an agent</h3><p>A broker gives your request to the agent best placed to help you.</p></li>
          <li><span>3</span><h3>Your agent takes it from there</h3><p>Homes that fit, viewings at times that work, and help with your offer.</p></li>
        </ol>
      </section>

      <section className="wl-role">
        <div className="wl-role-text">
          <p className="wl-kicker">For clients</p>
          <h2>Two minutes, then a real person helps</h2>
          <ul>
            <li>One short form for buying, selling or both</li>
            <li>You choose what to share; your details go only to your agent</li>
            <li>Once your agent invites you, follow every step in your own portal and message them any time</li>
          </ul>
          <Link className="button wl-btn-primary" to="/start">Tell us what you need</Link>
        </div>
        <ClientFlowArt />
      </section>

      <section className="wl-role wl-role-flip">
        <PipelineArt />
        <div className="wl-role-text">
          <p className="wl-kicker">For agents</p>
          <h2>Know what to do next, for every client</h2>
          <ul>
            <li>A seven-stage pipeline from new lead to won deal</li>
            <li>Match scores for 800 Illinois listings, and a calendar that never double-books</li>
            <li>An AI assistant suggests the next step and drafts the message. You decide.</li>
          </ul>
        </div>
      </section>

      <section className="wl-role">
        <div className="wl-role-text">
          <p className="wl-kicker">For brokers</p>
          <h2>See the whole office at a glance</h2>
          <ul>
            <li>New website requests wait for you to assign them</li>
            <li>Move clients between agents; their viewings move with them</li>
            <li>Add agents and brokers, and see everyone’s workload</li>
          </ul>
          {!user && <Link className="button wl-btn-dark" to="/login">Sign in as a broker</Link>}
        </div>
        <BrokerArt />
      </section>

      <section className="wl-trust">
        <h2>Built to be trusted</h2>
        <div className="wl-trust-grid">
          <div><h3>The AI suggests, people decide</h3><p>Nothing is ever sent to a client automatically.</p></div>
          <div><h3>Only real facts</h3><p>Every price, address and date in a suggestion is checked against the client’s file.</p></div>
          <div><h3>Each agent sees their own clients</h3><p>Brokers see everyone; agents never see each other’s clients.</p></div>
          <div><h3>Tested on every change</h3><p>Automated tests and security checks run before anything goes live.</p></div>
        </div>
      </section>

      <section className="wl-cta">
        <h2>Ready when you are</h2>
        <div className="wl-ctas">
          <Link className="button wl-btn-primary" to="/start">Find a home</Link>
          {signIn}
        </div>
      </section>

      <footer className="wl-foot">
        <p>PropConnect AI · A CPSC-8985 graduate project at Governors State University</p>
        <nav><Link to="/start">Find a home</Link><Link to="/portal/login">Client sign-in</Link><Link to="/login">Staff sign-in</Link></nav>
      </footer>
    </div>
  );
}
