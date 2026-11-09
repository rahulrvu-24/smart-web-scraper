"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";

import { api, API_URL, ApiError } from "@/lib/api";

//Part A: types, checks, helpers:

type CheckState =
  | { kind: "checking" }
  | { kind: "up"; ms: number }
  | { kind: "down"; reason: string };

type Check = {
  key: string;
  label: string;
  endpoint: string;
  run: () => Promise<unknown>;
};

const CHECKS: Check[] = [
  { key: "api", label: "API", endpoint: "/health", run: api.health },
  { key: "db", label: "Database", endpoint: "/health/db", run: api.dbHealth },
];

const POLL_MS = 10_000;

async function timed(run: () => Promise<unknown>): Promise<CheckState> {
  const start = performance.now();
  try {
    await run();
    return { kind: "up", ms: Math.round(performance.now() - start) };
  } catch (err) {
    const reason =
      err instanceof ApiError
        ? err.status === null
          ? "unreachable"
          : `${err.status} · ${err.message}`
        : "unexpected error";
    return { kind: "down", reason };
  }
}

function runAllChecks(): Promise<CheckState[]> {
  return Promise.all(CHECKS.map((c) => timed(c.run)));
}

//Part B: state and polling:

export default function StatusPage() {
  const [states, setStates] = useState<Record<string, CheckState>>(() =>
    Object.fromEntries(CHECKS.map((c) => [c.key, { kind: "checking" } as CheckState])),
  );
  const [checkedAt, setCheckedAt] = useState<Date | null>(null);

  const apply = useCallback((results: CheckState[]) => {
    setStates(Object.fromEntries(CHECKS.map((c, i) => [c.key, results[i]])));
    setCheckedAt(new Date());
  }, []);

  const refresh = () => runAllChecks().then(apply);

  useEffect(() => {
    let active = true;
    const tick = () =>
      runAllChecks().then((results) => {
        if (active) apply(results);
      });
    tick();
    const id = setInterval(tick, POLL_MS);
    return () => {
      active = false;
      clearInterval(id);
    };
  }, [apply]);

  const allUp = CHECKS.every((c) => states[c.key].kind === "up");
  const anyChecking = CHECKS.some((c) => states[c.key].kind === "checking");

  //Part C: what's drawn on screen:

  return (
    <main className="max-w-3xl mx-auto px-8 py-6">
      <nav className="flex items-center justify-between pb-16">
        <Link href="/" className="font-mono font-semibold text-lg">
          Smart Web Scraper
        </Link>
        <Link href="/" className="text-sm text-ink-muted hover:text-ink">
          ← Back home
        </Link>
      </nav>

      <h1 className="text-3xl font-bold tracking-tight">System status</h1>
      <p className="text-ink-muted mt-3">
        {anyChecking
          ? "Checking the backend…"
          : allUp
            ? "Everything is up."
            : "Something is down. Details below."}
      </p>

      <div className="mt-10 border-t border-line">
        {CHECKS.map((check) => {
          const state = states[check.key];
          return (
            <div key={check.key} className="flex items-center gap-6 py-5 border-b border-line">
              <span
                aria-hidden
                className={`w-2.5 h-2.5 shrink-0 ${
                  state.kind === "up" ? "bg-teal" : state.kind === "down" ? "bg-raw-tag" : "bg-gold"
                }`}
              />
              <div className="flex-1">
                <div className="font-semibold">{check.label}</div>
                <div className="font-mono text-xs text-ink-muted mt-1">GET {check.endpoint}</div>
              </div>
              <div className="font-mono text-sm text-right">
                {state.kind === "checking" && <span className="text-gold">checking</span>}
                {state.kind === "up" && <span className="text-teal">up · {state.ms} ms</span>}
                {state.kind === "down" && <span className="text-raw-tag">down · {state.reason}</span>}
              </div>
            </div>
          );
        })}
      </div>

      <div className="mt-6 flex items-center justify-between font-mono text-xs text-ink-muted">
        <span>
          {API_URL}
          {checkedAt && ` · checked ${checkedAt.toLocaleTimeString()}`}
        </span>
        <button onClick={refresh} className="border border-line px-4 py-2 text-ink hover:border-ink">
          Check again
        </button>
      </div>
    </main>
  );
}