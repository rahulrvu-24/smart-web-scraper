import Link from "next/link";

const steps: [string, string][] = [
  ["Submit a URL and a schema", "Tell it what fields you want back."],
  ["The backend validates the URL", "Private and internal targets are blocked before any request is made."],
  ["A sandboxed worker renders the page", "Including JavaScript-rendered content."],
  ["An LLM extracts your fields", "Only the fields you asked for, nothing more."],
  ["You get back structured JSON", "Validated against your schema, every time."],
];

const guardrails: [string, string][] = [
  ["SSRF protection", "Private IP ranges and internal hosts are blocked before any request is made."],
  ["Sandboxed execution", "Every page loads inside an isolated, short-lived container."],
  ["Schema validation", "Output is checked against your schema before it's ever returned."],
  ["Rate limits", "Per-user and per-domain limits keep both sides safe."],
];

const REPO_URL = "https://github.com/rahulrvu-24/smart-web-scraper";

const stack = ["Next.js", "FastAPI", "PostgreSQL", "Redis", "Playwright"];

export default function Home() {
  return (
    <main>
      <nav className="max-w-6xl mx-auto flex items-center justify-between px-8 py-6">
        <span className="font-mono font-semibold text-lg">Smart Web Scraper</span>
        <div className="flex items-center gap-8 text-sm text-ink-muted">
          <a href="#how" className="hover:text-ink">How it works</a>
          <a href="#security" className="hover:text-ink">Security</a>
          <Link href="/status" className="hover:text-ink">Status</Link>
          <a href={REPO_URL} className="hover:text-ink">GitHub</a>
        </div>
      </nav>

      <section className="max-w-6xl mx-auto px-8 grid md:grid-cols-2 gap-12 items-center pt-12 pb-20">
        <div>
          <h1 className="text-5xl font-bold leading-[1.1] tracking-tight">
            Turn any webpage
            <br />
            into structured JSON.
          </h1>
          <p className="text-ink-muted text-lg leading-relaxed mt-6 max-w-[38ch]">
            Give it a URL and the fields you want. It renders the page, pulls out what matters, and
            returns clean JSON, validated against your schema every time.
          </p>
          <div className="flex gap-4 mt-8">
            <a href={REPO_URL} className="bg-gold text-paper px-6 py-3 font-semibold">
              Get the code
            </a>
            <a href="#how" className="border border-line px-6 py-3">
              See how it works
            </a>
          </div>
        </div>

        <div className="font-mono text-[0.82rem] flex flex-col gap-3">
          <div className="border border-line bg-white p-5 opacity-90">
            <div className="text-raw-tag">&lt;div class=&quot;prc_9xk&quot;&gt;</div>
            <div className="text-raw-text">
              &nbsp;&nbsp;$42.<span className="opacity-40">&lt;!-- --&gt;</span>99
            </div>
            <div className="text-raw-tag">&lt;/div&gt;</div>
            <div className="text-raw-text opacity-60">&lt;script&gt;trackEvent(...)&lt;/script&gt;</div>
            <div className="text-raw-tag">&lt;h1 class=&quot;ttl-lg&quot;&gt;Wireless Headphones — Pro&lt;/h1&gt;</div>
            <div className="text-raw-text">★★★★☆ (2,341)</div>
          </div>
          <div className="text-center text-ink-muted">↓</div>
          <div className="border border-teal bg-white p-5">
            <div>{"{"}</div>
            <div>
              &nbsp;&nbsp;&quot;title&quot;: <span className="text-gold">&quot;Wireless Headphones Pro&quot;</span>,
            </div>
            <div>
              &nbsp;&nbsp;&quot;price&quot;: <span className="text-gold">42.99</span>,
            </div>
            <div>
              &nbsp;&nbsp;&quot;rating&quot;: <span className="text-gold">4.0</span>,
            </div>
            <div>
              &nbsp;&nbsp;&quot;reviews&quot;: <span className="text-gold">2341</span>
            </div>
            <div>{"}"}</div>
          </div>
        </div>
      </section>

      <section id="how" className="max-w-6xl mx-auto px-8 pb-20">
        <h2 className="text-2xl font-semibold mb-8">How it works</h2>
        {steps.map(([title, desc], i) => (
          <div key={title} className={`flex gap-6 py-6 border-b border-line ${i === 0 ? "border-t" : ""}`}>
            <div className="font-mono text-ink-muted w-8 shrink-0">{i + 1}</div>
            <div>
              <div className="font-semibold">{title}</div>
              <div className="text-ink-muted text-sm mt-1">{desc}</div>
            </div>
          </div>
        ))}
      </section>

      <section id="security" className="max-w-6xl mx-auto px-8 pb-20">
        <h2 className="text-2xl font-semibold mb-8">Built to say no to bad requests</h2>
        <div className="grid md:grid-cols-2 gap-x-12">
          {guardrails.map(([title, desc]) => (
            <div key={title} className="flex gap-3 py-5 border-t border-line">
              <span className="text-teal font-bold">✓</span>
              <div>
                <div className="font-semibold">{title}</div>
                <div className="text-ink-muted text-sm mt-1">{desc}</div>
              </div>
            </div>
          ))}
        </div>
      </section>

      <section className="max-w-6xl mx-auto px-8 pb-20">
        <div className="flex flex-wrap font-mono text-sm text-ink-muted">
          {stack.map((t, i) => (
            <span key={t} className={`px-5 ${i > 0 ? "border-l border-line" : ""}`}>
              {t}
            </span>
          ))}
        </div>
      </section>

      <footer className="max-w-6xl mx-auto px-8 py-8 border-t border-line flex justify-between text-ink-muted text-sm">
        <span className="font-mono">Smart Web Scraper</span>
        <span>Built as a full-stack AI project.</span>
      </footer>
    </main>
  );
}