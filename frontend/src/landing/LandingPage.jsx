import React, {Suspense, lazy, useEffect, useState} from 'react';
import './landing.css';

const HeroCanvas=lazy(()=>import('./HeroCanvas'));

const AGENTS=[
  {id:'product',name:'Product Intelligence Agent',copy:'Flags thin descriptions, urgency tactics, counterfeit wording, and attempts to manipulate AI reviewers.',tone:'#4269df'},
  {id:'seller',name:'Seller Verification Agent',copy:'Reads available reputation and history signals, off-platform contact, and unprotected payment requests.',tone:'#22ac8e'},
  {id:'price',name:'Price Analysis Agent',copy:'Checks discount plausibility against a supplied reference or a clearly labelled AI estimate.',tone:'#e6ad45'},
  {id:'policy',name:'Policy Analysis Agent',copy:'Reviews stated return and refund terms, windows, and delivery information when provided.',tone:'#5b84f0'},
  {id:'risk',name:'Risk Assessment Orchestrator',copy:'Combines specialist findings into a buyer-facing recommendation and overall risk indicator.',tone:'#1c2d4b'},
];

const STEPS=[
  {n:'01',title:'Discover',text:'Enter a product URL or the listing details you already have.'},
  {n:'02',title:'Investigate',text:'Specialist agents review product, seller, price, and policy signals.'},
  {n:'03',title:'Evaluate',text:'TrustPay surfaces findings, missing information, and a risk indicator.'},
  {n:'04',title:'Decide',text:'You approve or reject with a recorded human decision before any order.'},
  {n:'05',title:'Pay',text:'When approved, continue through the existing PayPal sandbox checkout.'},
];

const CAPABILITIES=[
  ['AI purchase analysis','Four specialist agents plus an orchestrator explain what they found.'],
  ['Seller signal review','Reputation cues, contact patterns, and unprotected-payment requests.'],
  ['Price evaluation','Discount plausibility against a reference or labelled estimate.'],
  ['Return policy reading','Stated windows and refund terms when the listing includes them.'],
  ['Risk identification','Heuristic indicators with supporting findings — not fraud probabilities.'],
  ['PayPal checkout','Human-approved sandbox orders through the existing payment integration.'],
];

function useReducedMotion(){
  const [reduced,setReduced]=useState(()=>typeof matchMedia==='function'&&matchMedia('(prefers-reduced-motion: reduce)').matches);
  useEffect(()=>{
    if(typeof matchMedia!=='function')return;
    const mq=matchMedia('(prefers-reduced-motion: reduce)');
    const on=()=>setReduced(mq.matches);
    mq.addEventListener?.('change',on);
    return ()=>mq.removeEventListener?.('change',on);
  },[]);
  return reduced;
}

function useReveal(reduced){
  useEffect(()=>{
    if(reduced){
      document.querySelectorAll('.lp-reveal').forEach(el=>el.classList.add('in'));
      return;
    }
    const io=new IntersectionObserver(entries=>{
      entries.forEach(e=>{if(e.isIntersecting)e.target.classList.add('in');});
    },{threshold:0.14,rootMargin:'0px 0px -8% 0px'});
    document.querySelectorAll('.lp-reveal').forEach(el=>io.observe(el));
    return ()=>io.disconnect();
  },[reduced]);
}

function ShieldIcon({size=22}){
  return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" aria-hidden="true"><path d="M12 3 4 6v6c0 5 8 9 8 9s8-4 8-9V6z" stroke="currentColor" strokeWidth="1.6"/><path d="m8 12 3 3 5-6" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round"/></svg>;
}

function DemoRisk(){
  return (
    <div className="demo-panel" aria-label="Demonstration risk assessment">
      <div className="demo-badge">Demonstration sample · not a live assessment</div>
      <div className="demo-grid">
        <div className="demo-score">
          <svg viewBox="0 0 120 120" role="img" aria-label="Sample risk score 38 of 100">
            <circle cx="60" cy="60" r="50" fill="none" stroke="#dfe7f5" strokeWidth="8"/>
            <circle cx="60" cy="60" r="50" fill="none" stroke="#20a889" strokeWidth="8" strokeDasharray={`${38*3.14159} 314.159`} strokeLinecap="round" transform="rotate(-90 60 60)"/>
          </svg>
          <div><strong>38</strong><span>RISK / 100</span><em>LOW</em></div>
        </div>
        <div className="demo-copy">
          <h3>Wireless ANC Headphones · Marketplace listing</h3>
          <p>Seller history looks consistent. Price is within a plausible range of comparable offers. Return window is stated as 30 days. One missing detail: shipping origin.</p>
          <ul>
            <li><span>Seller signals</span><b>Stable</b></li>
            <li><span>Price check</span><b>Plausible</b></li>
            <li><span>Return policy</span><b>Documented</b></li>
            <li><span>Watch item</span><b>Confirm shipping</b></li>
          </ul>
        </div>
      </div>
    </div>
  );
}

export default function LandingPage({onGetStarted,onLogin,onPrivacy,onTerms,theme='dark',setTheme}){
  const reduced=useReducedMotion();
  const [scrolled,setScrolled]=useState(false);
  const [menuOpen,setMenuOpen]=useState(false);
  const [activeAgent,setActiveAgent]=useState('product');
  const [webgl,setWebgl]=useState(true);
  useReveal(reduced);
  const dark=theme!=='light';

  useEffect(()=>{
    const onScroll=()=>setScrolled(window.scrollY>18);
    onScroll();
    window.addEventListener('scroll',onScroll,{passive:true});
    try{
      const c=document.createElement('canvas');
      const ok=!!(c.getContext('webgl')||c.getContext('experimental-webgl'));
      setWebgl(ok);
    }catch{setWebgl(false);}
    return ()=>window.removeEventListener('scroll',onScroll);
  },[]);

  function jump(id){
    setMenuOpen(false);
    const el=document.getElementById(id);
    if(el)el.scrollIntoView({behavior:reduced?'auto':'smooth',block:'start'});
  }

  return (
    <div className="landing-root">
      <a className="skip-link" href="#main">Skip to content</a>
      <header className={`lp-nav ${scrolled?'scrolled':''}`}>
        <div className="lp-nav-inner">
          <a className="lp-brand" href="#/" onClick={e=>{e.preventDefault();jump('top');}}>
            <span className="lp-mark"><ShieldIcon/></span>
            <span>TrustPay <em>AI</em></span>
          </a>
          <nav className={`lp-links ${menuOpen?'open':''}`} aria-label="Landing">
            <button type="button" onClick={()=>jump('top')}>Home</button>
            <button type="button" onClick={()=>jump('how')}>How It Works</button>
            <button type="button" onClick={()=>jump('features')}>Features</button>
            <button type="button" onClick={()=>jump('security')}>Security</button>
            <button type="button" onClick={()=>jump('about')}>About</button>
          </nav>
          <div className="lp-nav-actions">
            {setTheme&&<button type="button" className="lp-theme" aria-label={dark?'Switch to light theme':'Switch to dark theme'} aria-pressed={dark} onClick={()=>setTheme(dark?'light':'dark')}>{dark?'Light mode':'Dark mode'}</button>}
            <button type="button" className="lp-btn ghost" onClick={onLogin}>Login</button>
            <button type="button" className="lp-btn primary" onClick={onGetStarted}>Get Started</button>
            <button type="button" className="lp-menu" aria-expanded={menuOpen} aria-label="Menu" onClick={()=>setMenuOpen(v=>!v)}>
              <span/><span/><span/>
            </button>
          </div>
        </div>
      </header>

      <main id="main">
        <section className="lp-hero" id="top">
          <div className="lp-hero-bg" aria-hidden="true"/>
          <div className="lp-hero-copy">
            <p className="lp-brand-hero">TrustPay AI</p>
            <h1>Shop Smarter. Pay Safer.</h1>
            <p className="lp-lede">Your AI-powered commerce safety companion. Evaluate sellers, uncover hidden risks, understand purchase policies, and make confident buying decisions before you pay.</p>
            <div className="lp-cta-row">
              <button type="button" className="lp-btn primary lg" onClick={onGetStarted}>Get Started</button>
              <button type="button" className="lp-btn ghost lg" onClick={()=>jump('how')}>Explore How It Works</button>
            </div>
          </div>
          <div className="lp-hero-visual">
            {webgl?(
              <Suspense fallback={<div className="hero-fallback" aria-hidden="true"/>}>
                <HeroCanvas reducedMotion={reduced}/>
              </Suspense>
            ):<div className="hero-fallback" role="img" aria-label="Abstract security shield visualization"/>}
            <div className="hero-caption">Live-style evaluation scene · demonstration visual</div>
          </div>
        </section>

        <section className="lp-section lp-trust lp-reveal" id="features" aria-labelledby="trust-title">
          <div className="lp-wrap">
            <p className="lp-kicker">Capabilities</p>
            <h2 id="trust-title">What TrustPay actually does</h2>
            <p className="lp-section-lede">Built for clearer purchase decisions — grounded in the agents and PayPal sandbox flow already in the product.</p>
            <div className="capability-grid">
              {CAPABILITIES.map(([title,text])=>(
                <article key={title}>
                  <span className="cap-icon"><ShieldIcon size={18}/></span>
                  <h3>{title}</h3>
                  <p>{text}</p>
                </article>
              ))}
            </div>
          </div>
        </section>

        <section className="lp-section lp-how lp-reveal" id="how" aria-labelledby="how-title">
          <div className="lp-wrap">
            <p className="lp-kicker">Workflow</p>
            <h2 id="how-title">How TrustPay AI works</h2>
            <p className="lp-section-lede">A five-stage journey from listing to human-approved PayPal checkout.</p>
            <ol className="journey">
              {STEPS.map((s,i)=>(
                <li key={s.n} style={{'--i':i}}>
                  <span>{s.n}</span>
                  <h3>{s.title}</h3>
                  <p>{s.text}</p>
                </li>
              ))}
            </ol>
          </div>
        </section>

        <section className="lp-section lp-agents lp-reveal" id="agents" aria-labelledby="agents-title">
          <div className="lp-wrap agents-layout">
            <div>
              <p className="lp-kicker">Multi-agent review</p>
              <h2 id="agents-title">Specialists, then a clear recommendation</h2>
              <p className="lp-section-lede">Hover an agent to see how it feeds the central orchestrator. Claims match the live application’s agent roles.</p>
              <div className="agent-list" role="list">
                {AGENTS.map(a=>(
                  <button key={a.id} type="button" role="listitem" className={activeAgent===a.id?'active':''} style={{'--tone':a.tone}} onMouseEnter={()=>setActiveAgent(a.id)} onFocus={()=>setActiveAgent(a.id)} onClick={()=>setActiveAgent(a.id)}>
                    <strong>{a.name}</strong>
                    <span>{a.copy}</span>
                  </button>
                ))}
              </div>
            </div>
            <div className="agent-hub" aria-hidden="true">
              <div className="hub-core">AI hub</div>
              {AGENTS.map((a,i)=>{
                const angle=(i/AGENTS.length)*Math.PI*2-Math.PI/2;
                const x=Math.cos(angle)*118;
                const y=Math.sin(angle)*118;
                return <span key={a.id} className={`hub-node ${activeAgent===a.id?'on':''}`} style={{transform:`translate(${x}px, ${y}px)`,background:a.tone}}/>;
              })}
              <p>{AGENTS.find(a=>a.id===activeAgent)?.name}</p>
            </div>
          </div>
        </section>

        <section className="lp-section lp-demo lp-reveal" id="demo" aria-labelledby="demo-title">
          <div className="lp-wrap">
            <p className="lp-kicker">Sample assessment</p>
            <h2 id="demo-title">See the decision surface</h2>
            <p className="lp-section-lede">A realistic illustration of how findings appear before you approve payment. Sample data only.</p>
            <DemoRisk/>
          </div>
        </section>

        <section className="lp-section lp-paypal lp-reveal" id="paypal" aria-labelledby="paypal-title">
          <div className="lp-wrap paypal-layout">
            <div>
              <p className="lp-kicker">Checkout</p>
              <h2 id="paypal-title">Analyze → Evaluate → Approve → Pay with PayPal</h2>
              <p className="lp-section-lede">TrustPay never creates a PayPal order until you approve. Secrets stay on the server. Status comes from the backend — this page does not simulate payment success.</p>
              <ol className="paypal-steps">
                <li>Review the assessment and acknowledge risk when required.</li>
                <li>Approve the purchase in the existing workspace.</li>
                <li>Continue to PayPal sandbox with the order the API created.</li>
                <li>Return to TrustPay to inspect capture status and the audit trail.</li>
              </ol>
              <button type="button" className="lp-btn primary" onClick={onGetStarted}>Open the workspace</button>
            </div>
            <div className="paypal-card" aria-hidden="true">
              <div className="paypal-brand"><span className="paypal-p">P</span> PayPal</div>
              <div className="paypal-lines">
                <div><span>Purchase</span><b>Sample headphones</b></div>
                <div><span>Risk</span><b>Low · human gate</b></div>
                <div><span>Action</span><b>Approve, then pay</b></div>
              </div>
              <div className="paypal-cta">Continue in TrustPay workspace</div>
              <p>Official PayPal marks describe the integration. This is not a live charge.</p>
            </div>
          </div>
        </section>

        <section className="lp-section lp-security lp-reveal" id="security" aria-labelledby="security-title">
          <div className="lp-wrap security-layout">
            <div className="security-visual" aria-hidden="true">
              <div className="shield-3d"><ShieldIcon size={64}/></div>
            </div>
            <div>
              <p className="lp-kicker">Security & privacy</p>
              <h2 id="security-title">Control stays with you</h2>
              <ul className="security-list">
                <li>Purchase risk analysis with transparent findings</li>
                <li>Seller credibility signals from available listing context</li>
                <li>Explicit human approval before order creation</li>
                <li>Payment processing through the existing PayPal integration</li>
                <li>Service secrets kept server-side — not in frontend <code>VITE_</code> variables</li>
              </ul>
              <p className="fine-print">TrustPay does not claim 100% protection or guaranteed fraud prevention.</p>
            </div>
          </div>
        </section>

        <section className="lp-section lp-about lp-reveal" id="about" aria-labelledby="about-title">
          <div className="lp-wrap about-narrow">
            <p className="lp-kicker">About</p>
            <h2 id="about-title">Built for the PayPal AI Hackathon</h2>
            <p>TrustPay AI is a sandbox prototype that combines specialist agents, an explainable risk report, Channel3 comparisons, and human-approved PayPal checkout. External retailer links are for comparison; TrustPay does not purchase from those retailers on your behalf.</p>
          </div>
        </section>

        <section className="lp-final lp-reveal" aria-labelledby="final-title">
          <div className="lp-final-bg" aria-hidden="true"/>
          <div className="lp-wrap final-inner">
            <h2 id="final-title">Confidence Should Be Part of Every Purchase.</h2>
            <p>Don't leave your next purchase to chance. Let TrustPay AI help you make informed decisions before you pay.</p>
            <button type="button" className="lp-btn primary lg" onClick={onGetStarted}>Get Started</button>
          </div>
        </section>
      </main>

      <footer className="lp-footer">
        <div className="lp-wrap footer-grid">
          <div>
            <div className="lp-brand footer-brand"><span className="lp-mark"><ShieldIcon/></span><span>TrustPay <em>AI</em></span></div>
            <p>AI-assisted purchase review with human approval and PayPal sandbox checkout.</p>
          </div>
          <div>
            <h3>Explore</h3>
            <button type="button" onClick={()=>jump('how')}>How It Works</button>
            <button type="button" onClick={()=>jump('features')}>Features</button>
            <button type="button" onClick={()=>jump('security')}>Security</button>
          </div>
          <div>
            <h3>Workspace</h3>
            <button type="button" onClick={onGetStarted}>Get Started</button>
            <button type="button" onClick={onLogin}>Login / Connect</button>
          </div>
          <div>
            <h3>Legal</h3>
            <button type="button" onClick={onPrivacy}>Privacy Policy</button>
            <button type="button" onClick={onTerms}>Terms & Conditions</button>
          </div>
        </div>
        <div className="lp-wrap footer-bottom">
          <span>© {new Date().getFullYear()} TrustPay AI · Sandbox prototype</span>
          <span>No fabricated social profiles in this build</span>
        </div>
      </footer>
    </div>
  );
}
