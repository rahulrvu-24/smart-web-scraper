"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import AppShell from "@/components/AppShell";
import JsonView from "@/components/JsonView";
import { Alert, Button, Panel, StatusBadge } from "@/components/ui";
import { api, type Job, type JobStatus } from "@/lib/api";
import { duration } from "@/lib/format";

const STEPS: { status: JobStatus[]; label: string }[] = [
  { status: ["queued", "running", "succeeded", "failed"], label: "Queued" },
  { status: ["running", "succeeded", "failed"], label: "Fetching + extracting" },
  { status: ["succeeded", "failed"], label: "Done" },
];

function Progress({ status }: { status: JobStatus }) {
  return (
    <ol className="flex items-center gap-3 font-mono text-xs">
      {STEPS.map((step, i) => {
        const reached = step.status.includes(status);
        const current = reached && !STEPS[i + 1]?.status.includes(status);
        return (
          <li key={step.label} className="flex items-center gap-3">
            {i > 0 && <span className={`w-8 h-px ${reached ? "bg-ink" : "bg-line"}`} />}
            <span className={reached ? (current && status !== "succeeded" && status !== "failed" ? "text-gold" : "text-ink") : "text-raw-text"}>
              {step.label}
            </span>
          </li>
        );
      })}
    </ol>
  );
}

function Value({ value }: { value: unknown }) {
  if (value === null || value === undefined) return <span className="text-raw-text">not found</span>;
  if (Array.isArray(value)) {
    if (value.length === 0) return <span className="text-raw-text">empty list</span>;
    return (
      <ul className="list-disc pl-4 space-y-0.5">
        {value.map((v, i) => (
          <li key={i}>{String(v)}</li>
        ))}
      </ul>
    );
  }
  if (typeof value === "boolean") return <span className="font-mono text-teal">{value ? "yes" : "no"}</span>;
  if (typeof value === "number") return <span className="font-mono">{value}</span>;
  return <span>{String(value)}</span>;
}

function JobDetail({ id }: { id: string }) {
  const router = useRouter();
  const [job, setJob] = useState<Job | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const inProgress = job === null || job.status === "queued" || job.status === "running";
  useEffect(() => {
    if (!inProgress) return;
    let cancelled = false;
    const load = () =>
      api
        .getJob(id)
        .then((j) => {
          if (!cancelled) setJob(j);
        })
        .catch((err) => {
          if (!cancelled) setError(err instanceof Error ? err.message : "Could not load the job");
        });
    load();
    const timer = setInterval(load, 1500);
    return () => {
      cancelled = true;
      clearInterval(timer);
    };
  }, [id, inProgress]);

  const retry = async () => {
    setBusy(true);
    try {
      setJob(await api.retryJob(id));
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not retry");
    } finally {
      setBusy(false);
    }
  };

  const remove = async () => {
    if (!window.confirm("Delete this job and its result?")) return;
    setBusy(true);
    try {
      await api.deleteJob(id);
      router.push("/dashboard");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not delete");
      setBusy(false);
    }
  };

  if (!job) {
    return error ? <Alert>{error}</Alert> : <p className="text-sm text-ink-muted font-mono">Loading job…</p>;
  }

  const result = job.result;
  const total = duration(job.started_at, job.finished_at);

  return (
    <div className="flex flex-col gap-6">
      <div>
        <Link href="/dashboard" className="text-sm text-ink-muted hover:text-ink">
          ← Dashboard
        </Link>
        <div className="flex flex-wrap items-start justify-between gap-4 mt-3">
          <div className="min-w-0">
            <h1 className="text-xl font-bold tracking-tight break-all">{result?.page_title || job.url}</h1>
            <a href={job.url} target="_blank" rel="noreferrer" className="font-mono text-xs text-ink-muted hover:text-ink break-all">
              {job.url}
            </a>
          </div>
          <div className="flex gap-2">
            {job.status === "failed" && (
              <Button onClick={retry} disabled={busy}>
                Retry
              </Button>
            )}
            <Button variant="danger" onClick={remove} disabled={busy}>
              Delete
            </Button>
          </div>
        </div>
      </div>

      {error && <Alert>{error}</Alert>}

      <div className="flex flex-wrap items-center gap-x-8 gap-y-3 border-y border-line py-4">
        <StatusBadge status={job.status} />
        <Progress status={job.status} />
        {job.attempts > 1 && <span className="font-mono text-xs text-ink-muted">attempt {job.attempts}</span>}
      </div>

      {job.status === "failed" && job.error_message && <Alert>{job.error_message}</Alert>}
      {job.status === "queued" && job.error_message && (
        <Alert tone="info">Previous attempt failed ({job.error_message}). Retrying automatically.</Alert>
      )}
      {inProgress && !job.error_message && (
        <p className="text-sm text-ink-muted">
          The worker is loading the page{job.render_js ? " in a headless browser and scrolling it" : ""} and asking the
          model for your fields. This usually takes {job.render_js ? "15–40" : "5–20"} seconds.
        </p>
      )}

      {result && (
        <>
          {!result.is_valid && (
            <Alert>
              The model&apos;s answer didn&apos;t fully match your field types:
              <ul className="list-disc pl-5 mt-1 font-mono text-xs">
                {(result.validation_errors ?? []).map((e) => (
                  <li key={e}>{e}</li>
                ))}
              </ul>
            </Alert>
          )}
          <div className="grid grid-cols-[minmax(0,1fr)] lg:grid-cols-[minmax(0,1fr)_minmax(0,1fr)] gap-6 items-start">
            <Panel title="Extracted fields">
              <table className="w-full text-sm">
                <tbody>
                  {Object.entries(job.fields).map(([name, spec]) => (
                    <tr key={name} className="border-b border-line last:border-b-0 align-top">
                      <th className="text-left font-normal py-2.5 pr-4 w-2/5">
                        <div className="font-mono">{name}</div>
                        <div className="text-xs text-ink-muted">{spec.type}</div>
                      </th>
                      <td className="py-2.5">
                        <Value value={result.data[name]} />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </Panel>
            <div>
              <h2 className="font-semibold mb-3">JSON</h2>
              <JsonView value={result.data} filename={`extraction-${job.id.slice(0, 8)}.json`} />
            </div>
          </div>
          <Panel title="How it ran">
            <dl className="grid grid-cols-2 md:grid-cols-4 gap-x-6 gap-y-4 text-sm">
              {[
                [
                  "Fetched with",
                  (result.fetch_method === "browser" ? "Headless Chromium" : "Plain HTTP") +
                    (job.render_js ? " (render JavaScript on)" : ""),
                ],
                ["Model", result.llm_model ?? "—"],
                ["Tokens in / out", `${result.input_tokens} / ${result.output_tokens}`],
                ["LLM time", result.latency_ms != null ? `${(result.latency_ms / 1000).toFixed(1)} s` : "—"],
                ["Total time", total ?? "—"],
                ["Schema valid", result.is_valid ? "yes" : "no"],
                ["Attempts", String(job.attempts)],
                ["Final URL", result.final_url ?? job.url],
              ].map(([label, value]) => (
                <div key={label} className="min-w-0">
                  <dt className="text-xs uppercase tracking-wide text-ink-muted">{label}</dt>
                  <dd className="font-mono text-xs mt-1 break-all">{value}</dd>
                </div>
              ))}
            </dl>
          </Panel>
        </>
      )}
    </div>
  );
}

export default function JobPage() {
  const { id } = useParams<{ id: string }>();
  return <AppShell>{id && <JobDetail id={id} />}</AppShell>;
}
