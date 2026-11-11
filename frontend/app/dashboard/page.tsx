"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useState, type FormEvent } from "react";

import AppShell from "@/components/AppShell";
import FieldBuilder from "@/components/FieldBuilder";
import { Alert, Button, Input, Label, Panel, Select, StatusBadge } from "@/components/ui";
import { api, type JobSummary, type Schema, type UsageSummary } from "@/lib/api";
import { fieldsFromRows, newRow, PRESETS, rowsFromFields, type FieldRow } from "@/lib/fields";
import { duration, shortUrl, timeAgo } from "@/lib/format";

const CUSTOM = "custom";

function NewJobForm({ schemas, onSchemaSaved }: { schemas: Schema[]; onSchemaSaved: () => void }) {
  const router = useRouter();
  const [url, setUrl] = useState("");
  const [schemaId, setSchemaId] = useState<string>(CUSTOM);
  const [rows, setRows] = useState<FieldRow[]>(() => [newRow("title", "string", "")]);
  const [saveName, setSaveName] = useState("");
  const [renderJs, setRenderJs] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const applyPreset = (index: number) => {
    const preset = PRESETS[index];
    setUrl(preset.url);
    setSchemaId(CUSTOM);
    setRows(preset.fields.map(([name, type, hint]) => newRow(name, type, hint)));
    setError(null);
  };

  const chooseSchema = (id: string) => {
    setSchemaId(id);
    const schema = schemas.find((s) => s.id === id);
    if (schema) setRows(rowsFromFields(schema.fields));
  };

  const saveAsSchema = async () => {
    const { fields, error: fieldError } = fieldsFromRows(rows);
    if (fieldError) return setError(fieldError);
    if (!saveName.trim()) return setError("Give the schema a name first.");
    setBusy(true);
    setError(null);
    try {
      const schema = await api.createSchema({ name: saveName.trim(), fields });
      setNotice(`Saved as "${schema.name}". You can reuse it from the dropdown.`);
      setSaveName("");
      onSchemaSaved();
      setSchemaId(schema.id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save the schema");
    } finally {
      setBusy(false);
    }
  };

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setNotice(null);
    let body;
    if (schemaId === CUSTOM) {
      const { fields, error: fieldError } = fieldsFromRows(rows);
      if (fieldError) return setError(fieldError);
      body = { url: url.trim(), fields, render_js: renderJs };
    } else {
      body = { url: url.trim(), schema_id: schemaId, render_js: renderJs };
    }
    setBusy(true);
    try {
      const job = await api.createJob(body);
      router.push(`/jobs/${job.id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not start the job");
      setBusy(false);
    }
  };

  return (
    <Panel title="New extraction">
      <form onSubmit={submit} className="flex flex-col gap-5">
        <div className="flex flex-wrap items-center gap-2 text-sm">
          <span className="text-ink-muted">Try an example:</span>
          {PRESETS.map((p, i) => (
            <button
              key={p.label}
              type="button"
              onClick={() => applyPreset(i)}
              className="border border-line px-2.5 py-1 font-mono text-xs hover:border-ink"
            >
              {p.label}
            </button>
          ))}
        </div>

        <div>
          <Label htmlFor="url">Page URL</Label>
          <Input
            id="url"
            type="url"
            required
            placeholder="https://example.com/product/123"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            className="font-mono"
          />
        </div>

        <div>
          <Label htmlFor="schema">Fields</Label>
          <Select id="schema" value={schemaId} onChange={(e) => chooseSchema(e.target.value)}>
            <option value={CUSTOM}>Custom fields (edit below)</option>
            {schemas.map((s) => (
              <option key={s.id} value={s.id}>
                Saved schema: {s.name} (v{s.version})
              </option>
            ))}
          </Select>
        </div>

        {schemaId === CUSTOM ? (
          <>
            <FieldBuilder rows={rows} onChange={setRows} />
            <div className="flex flex-wrap items-end gap-2 border-t border-line pt-4">
              <div className="flex-1 min-w-48">
                <Label htmlFor="save-name">Save these fields for later (optional)</Label>
                <Input id="save-name" placeholder="e.g. product" value={saveName} onChange={(e) => setSaveName(e.target.value)} />
              </div>
              <Button type="button" onClick={saveAsSchema} disabled={busy || !saveName.trim()}>
                Save schema
              </Button>
            </div>
          </>
        ) : (
          <ul className="flex flex-wrap gap-2">
            {rows.map((r) => (
              <li key={r.key} className="border border-line px-2.5 py-1 font-mono text-xs">
                {r.name} <span className="text-ink-muted">· {r.type}</span>
              </li>
            ))}
          </ul>
        )}

        <label className="flex items-start gap-3 text-sm cursor-pointer select-none">
          <input
            type="checkbox"
            className="mt-0.5 h-4 w-4 accent-[var(--color-teal)]"
            checked={renderJs}
            onChange={(e) => setRenderJs(e.target.checked)}
          />
          <span>
            <span className="font-semibold">Render JavaScript</span>
            <span className="block text-ink-muted text-xs mt-0.5">
              Loads the page in a headless browser and scrolls to load more items. Use it for shops and apps whose
              products appear only after the page loads. Slower (10–30 s).
            </span>
          </span>
        </label>

        {error && <Alert>{error}</Alert>}
        {notice && <Alert tone="info">{notice}</Alert>}

        <div>
          <Button type="submit" variant="primary" disabled={busy || !url.trim()}>
            {busy ? "Starting…" : "Extract JSON"}
          </Button>
        </div>
      </form>
    </Panel>
  );
}

function RecentJobs({ jobs, total }: { jobs: JobSummary[] | null; total: number }) {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 30_000);
    return () => clearInterval(id);
  }, []);

  return (
    <Panel title="Recent jobs" action={<span className="font-mono text-xs text-ink-muted">{total} total</span>}>
      {jobs === null ? (
        <p className="text-sm text-ink-muted font-mono">Loading…</p>
      ) : jobs.length === 0 ? (
        <p className="text-sm text-ink-muted">No jobs yet. Pick an example above and press Extract JSON.</p>
      ) : (
        <ul className="-my-3">
          {jobs.map((job) => (
            <li key={job.id} className="border-b border-line last:border-b-0">
              <Link href={`/jobs/${job.id}`} className="flex items-center gap-4 py-3 hover:bg-paper -mx-2 px-2">
                <span className="w-24 shrink-0">
                  <StatusBadge status={job.status} />
                </span>
                <span className="flex-1 min-w-0 truncate font-mono text-sm" title={job.url}>
                  {shortUrl(job.url)}
                </span>
                <span className="hidden sm:block text-xs text-ink-muted font-mono w-16 text-right">
                  {duration(job.started_at, job.finished_at) ?? ""}
                </span>
                <span className="text-xs text-ink-muted w-20 text-right">{timeAgo(job.created_at, now)}</span>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </Panel>
  );
}

function UsagePanel({ usage }: { usage: UsageSummary | null }) {
  if (!usage) return null;
  const done = usage.jobs_by_status.succeeded ?? 0;
  const failed = usage.jobs_by_status.failed ?? 0;
  const stats: [string, string][] = [
    ["Jobs succeeded", `${done}${failed ? ` / ${done + failed}` : ""}`],
    ["LLM calls", `${usage.llm_calls}${usage.failed_llm_calls ? ` (${usage.failed_llm_calls} failed)` : ""}`],
    ["Tokens in / out", `${usage.input_tokens.toLocaleString()} / ${usage.output_tokens.toLocaleString()}`],
    ["Fallback model used", `${usage.fallback_used}×`],
  ];
  return (
    <Panel title="Usage">
      <dl className="grid grid-cols-2 gap-x-6 gap-y-4">
        {stats.map(([label, value]) => (
          <div key={label}>
            <dt className="text-xs uppercase tracking-wide text-ink-muted">{label}</dt>
            <dd className="font-mono text-sm mt-1">{value}</dd>
          </div>
        ))}
      </dl>
      {usage.by_model.length > 0 && (
        <table className="w-full text-xs font-mono mt-5 border-t border-line">
          <thead>
            <tr className="text-ink-muted text-left">
              <th className="font-normal py-2">Model</th>
              <th className="font-normal py-2 text-right">Calls</th>
              <th className="font-normal py-2 text-right">Avg time</th>
            </tr>
          </thead>
          <tbody>
            {usage.by_model.map((m) => (
              <tr key={m.model} className="border-t border-line">
                <td className="py-2 break-all pr-2">{m.model}</td>
                <td className="py-2 text-right">
                  {m.calls}
                  {m.failed_calls > 0 && <span className="text-raw-tag"> ({m.failed_calls} failed)</span>}
                </td>
                <td className="py-2 text-right">{(m.avg_latency_ms / 1000).toFixed(1)} s</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </Panel>
  );
}

function Dashboard() {
  const [schemas, setSchemas] = useState<Schema[]>([]);
  const [jobs, setJobs] = useState<JobSummary[] | null>(null);
  const [total, setTotal] = useState(0);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [usage, setUsage] = useState<UsageSummary | null>(null);

  const loadSchemas = useCallback(() => {
    api.listSchemas().then(setSchemas).catch(() => {});
  }, []);

  useEffect(() => {
    loadSchemas();
  }, [loadSchemas]);

  // Poll quickly while any job is still in progress, slowly otherwise.
  const active = jobs?.some((j) => j.status === "queued" || j.status === "running") ?? false;
  useEffect(() => {
    let cancelled = false;
    const load = () =>
      api
        .listJobs(15)
        .then((page) => {
          if (cancelled) return;
          setJobs(page.items);
          setTotal(page.total);
          setLoadError(null);
        })
        .then(() => api.usage())
        .then((u) => {
          if (!cancelled && u) setUsage(u);
        })
        .catch((err) => {
          if (!cancelled) setLoadError(err instanceof Error ? err.message : "Could not load jobs");
        });
    load();
    const id = setInterval(load, active ? 2000 : 15000);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, [active]);

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Dashboard</h1>
        <p className="text-ink-muted text-sm mt-1">Give it a URL and the fields you want back.</p>
      </div>
      {loadError && <Alert>{loadError}</Alert>}
      <div className="grid grid-cols-[minmax(0,1fr)] lg:grid-cols-[minmax(0,1.25fr)_minmax(0,1fr)] gap-6 items-start">
        <NewJobForm schemas={schemas} onSchemaSaved={loadSchemas} />
        <div className="flex flex-col gap-6">
          <RecentJobs jobs={jobs} total={total} />
          <UsagePanel usage={usage} />
        </div>
      </div>
    </div>
  );
}

export default function DashboardPage() {
  return (
    <AppShell>
      <Dashboard />
    </AppShell>
  );
}
