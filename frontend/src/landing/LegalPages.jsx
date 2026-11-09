import React from 'react';
import './landing.css';

function Shell({title, children, onHome, onGetStarted, theme='dark', setTheme}){
  const dark=theme!=='light';
  return (
    <div className="landing-root legal-page">
      <header className="lp-nav solid">
        <div className="lp-nav-inner">
          <a className="lp-brand" href="#/" onClick={e=>{e.preventDefault();onHome();}}>
            <span className="lp-mark" aria-hidden="true">
              <svg width="22" height="22" viewBox="0 0 24 24" fill="none"><path d="M12 3 4 6v6c0 5 8 9 8 9s8-4 8-9V6z" stroke="currentColor" strokeWidth="1.6"/><path d="m8 12 3 3 5-6" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round"/></svg>
            </span>
            <span>TrustPay <em>AI</em></span>
          </a>
          <div className="lp-nav-actions">
            {setTheme&&<button type="button" className="lp-theme" aria-label={dark?'Switch to light theme':'Switch to dark theme'} aria-pressed={dark} onClick={()=>setTheme(dark?'light':'dark')}>{dark?'Light mode':'Dark mode'}</button>}
            <button type="button" className="lp-btn ghost" onClick={onHome}>Home</button>
            <button type="button" className="lp-btn primary" onClick={onGetStarted}>Get Started</button>
          </div>
        </div>
      </header>
      <main className="legal-main">
        <p className="lp-kicker">TrustPay AI</p>
        <h1>{title}</h1>
        <p className="legal-updated">Last updated: 9 November 2026 (Asia/Calcutta)</p>
        <div className="legal-body">{children}</div>
      </main>
    </div>
  );
}

export function PrivacyPage({onHome,onGetStarted,theme,setTheme}){
  return (
    <Shell title="Privacy Policy" onHome={onHome} onGetStarted={onGetStarted} theme={theme} setTheme={setTheme}>
      <p>This policy describes how the TrustPay AI sandbox prototype handles information when you use the local or hosted application.</p>
      <h2>Information we process</h2>
      <ul>
        <li><strong>Purchase details you submit</strong> — product URLs or manual listing fields (title, price, seller, description, return policy, seller messages) used to run assessments.</li>
        <li><strong>Assessment and payment records</strong> — stored in the configured SQLite database on the server that runs the API.</li>
        <li><strong>Access key</strong> — if configured, your TrustPay API access key is entered in the browser and kept in memory for the session; it is not written to frontend environment variables.</li>
        <li><strong>Theme preference</strong> — light/dark theme may be stored in <code>localStorage</code> on your device.</li>
        <li><strong>Checkout language preference</strong> — may be stored in <code>localStorage</code>.</li>
      </ul>
      <h2>Service credentials</h2>
      <p>PayPal, LLM, and Channel3 credentials belong in server-side environment configuration. They are not intended to be exposed to the browser.</p>
      <h2>Payments</h2>
      <p>Checkout uses PayPal’s sandbox (or configured) APIs. TrustPay does not collect or store your PayPal password. Payment status is confirmed through the backend after PayPal redirects or webhook verification when configured.</p>
      <h2>Third-party processing</h2>
      <ul>
        <li>AI providers process listing text you submit when the LLM is enabled.</li>
        <li>Channel3 may receive product search queries for comparison offers.</li>
        <li>PayPal processes order creation, approval, and capture.</li>
      </ul>
      <h2>Cookies and tracking</h2>
      <p>This marketing page does not set non-essential advertising cookies. The workspace uses browser storage only for theme and locale preferences.</p>
      <h2>Limitations</h2>
      <p>Risk scores are heuristic indicators, not fraud probabilities or guarantees. Missing information remains unknown; seller claims are not independently verified facts.</p>
      <h2>Contact</h2>
      <p>For questions about this prototype, use the project repository maintainers. No separate support email is published in this build.</p>
    </Shell>
  );
}

export function TermsPage({onHome,onGetStarted,theme,setTheme}){
  return (
    <Shell title="Terms & Conditions" onHome={onHome} onGetStarted={onGetStarted} theme={theme} setTheme={setTheme}>
      <p>These terms apply to the TrustPay AI hackathon / sandbox prototype.</p>
      <h2>Nature of the service</h2>
      <p>TrustPay AI assists buyers in reviewing purchase signals with specialist agents and requires a recorded human decision before creating a PayPal order in supported flows. It is a prototype, not a licensed financial advisory or fraud-insurance product.</p>
      <h2>No guarantees</h2>
      <ul>
        <li>Assessments can be incomplete when listing data is thin or an LLM is unavailable (rules-only mode).</li>
        <li>Channel3 results are comparison candidates, not seller verification.</li>
        <li>External retailer links are not purchases executed by TrustPay.</li>
        <li>PayPal hosted-page language and appearance may follow PayPal account or regional preferences.</li>
      </ul>
      <h2>Your responsibilities</h2>
      <p>You remain responsible for purchase decisions, for using sandbox credentials only in test environments, and for protecting API keys and secrets.</p>
      <h2>Payments</h2>
      <p>Orders are created only after your explicit approval in the application. TrustPay does not bypass backend order creation, capture, or verification. Sandbox payments use test funds when configured for sandbox.</p>
      <h2>Intellectual property</h2>
      <p>TrustPay AI branding and application code are provided under the project’s published license. PayPal marks belong to PayPal; their appearance here describes integration and does not imply endorsement beyond the integration itself.</p>
      <h2>Availability</h2>
      <p>The service may change, break, or be withdrawn without notice as a prototype.</p>
    </Shell>
  );
}
