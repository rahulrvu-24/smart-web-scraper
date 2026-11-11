"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import AppShell from "@/components/AppShell";
import { Alert, Panel } from "@/components/ui";
import { api, type ActivityItem } from "@/lib/api";

const LABELS: Record<string, string> = {
  "auth.register": "Created account",
  "auth.login": "Logged in",
  "auth.login_failed": "Failed login attempt",
  "schema.create": "Created schema",
  "schema.update": "Edited schema",
  "schema.delete": "Deleted schema",
  "job.create": "Started job",
  "job.retry": "Retried job",
  "job.delete": "Deleted job",
  "job.blocked_url": "Blocked URL",
};

function describe(item: ActivityItem): string {
  const d = item.details ?? {};
  if (typeof d.name === "string") return d.name;
  if (typeof d.url === "string") return d.url;
  if (typeof d.version === "number") return `now v${d.version}`;
  return "";
}

function Activity() {
  const [items, setItems] = useState<ActivityItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .activity()
      .then(setItems)
      .catch((err) => setError(err instanceof Error ? err.message : "Could not load activity"));
  }, []);

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Activity</h1>
        <p className="text-ink-muted text-sm mt-1">Everything done on your account, newest first, from the audit log.</p>
      </div>
      {error && <Alert>{error}</Alert>}
      <Panel>
        {items === null ? (
          <p className="text-sm text-ink-muted font-mono">Loading…</p>
        ) : (
          <ul className="-my-3">
            {items.map((item) => {
              const warn = item.action === "auth.login_failed" || item.action === "job.blocked_url";
              const jobLink = item.target_type === "scrape_job" && item.action !== "job.delete" && item.target_id;
              return (
                <li key={item.id} className="grid grid-cols-[9rem_1fr] sm:grid-cols-[10rem_12rem_1fr_8rem] gap-x-4 gap-y-1 py-3 border-b border-line last:border-b-0 text-sm">
                  <span className="font-mono text-xs text-ink-muted">{new Date(item.created_at).toLocaleString()}</span>
                  <span className={warn ? "text-raw-tag font-semibold" : "font-semibold"}>{LABELS[item.action] ?? item.action}</span>
                  <span className="col-span-2 sm:col-span-1 font-mono text-xs text-ink-muted truncate" title={describe(item)}>
                    {jobLink ? (
                      <Link href={`/jobs/${item.target_id}`} className="hover:text-ink underline">
                        {describe(item) || "open job"}
                      </Link>
                    ) : (
                      describe(item)
                    )}
                  </span>
                  <span className="hidden sm:block font-mono text-xs text-ink-muted text-right">{item.ip_address}</span>
                </li>
              );
            })}
          </ul>
        )}
      </Panel>
    </div>
  );
}

export default function ActivityPage() {
  return (
    <AppShell>
      <Activity />
    </AppShell>
  );
}
