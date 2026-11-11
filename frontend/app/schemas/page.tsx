"use client";

import { useCallback, useEffect, useState, type FormEvent } from "react";

import AppShell from "@/components/AppShell";
import FieldBuilder from "@/components/FieldBuilder";
import { Alert, Button, Input, Label, Panel } from "@/components/ui";
import { api, type Schema } from "@/lib/api";
import { fieldsFromRows, newRow, rowsFromFields, type FieldRow } from "@/lib/fields";

type Draft = { id: string | null; name: string; description: string; rows: FieldRow[] };
const emptyDraft = (): Draft => ({ id: null, name: "", description: "", rows: [newRow()] });

function SchemaEditor({ draft, onDone }: { draft: Draft; onDone: () => void }) {
  const [state, setState] = useState(draft);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    const { fields, error: fieldError } = fieldsFromRows(state.rows);
    if (fieldError) return setError(fieldError);
    setBusy(true);
    setError(null);
    const body = { name: state.name.trim(), description: state.description.trim() || null, fields };
    try {
      if (state.id) await api.updateSchema(state.id, body);
      else await api.createSchema(body);
      onDone();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save");
      setBusy(false);
    }
  };

  return (
    <Panel title={state.id ? `Edit "${draft.name}"` : "New schema"}>
      <form onSubmit={submit} className="flex flex-col gap-4">
        <div className="grid md:grid-cols-2 gap-4">
          <div>
            <Label htmlFor="name">Name</Label>
            <Input id="name" required maxLength={100} value={state.name} onChange={(e) => setState({ ...state, name: e.target.value })} />
          </div>
          <div>
            <Label htmlFor="description">Description (optional)</Label>
            <Input
              id="description"
              maxLength={1000}
              value={state.description}
              onChange={(e) => setState({ ...state, description: e.target.value })}
            />
          </div>
        </div>
        <FieldBuilder rows={state.rows} onChange={(rows) => setState({ ...state, rows })} />
        {error && <Alert>{error}</Alert>}
        <div className="flex gap-2">
          <Button type="submit" variant="primary" disabled={busy || !state.name.trim()}>
            {state.id ? "Save changes" : "Create schema"}
          </Button>
          <Button type="button" onClick={onDone} disabled={busy}>
            Cancel
          </Button>
        </div>
      </form>
    </Panel>
  );
}

function Schemas() {
  const [schemas, setSchemas] = useState<Schema[] | null>(null);
  const [draft, setDraft] = useState<Draft | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    api
      .listSchemas()
      .then(setSchemas)
      .catch((err) => setError(err instanceof Error ? err.message : "Could not load schemas"));
  }, []);
  useEffect(() => {
    load();
  }, [load]);

  const remove = async (schema: Schema) => {
    if (!window.confirm(`Delete "${schema.name}"? Jobs that used it keep their results.`)) return;
    try {
      await api.deleteSchema(schema.id);
      load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not delete");
    }
  };

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Schemas</h1>
          <p className="text-ink-muted text-sm mt-1">Saved sets of fields you can reuse for any URL.</p>
        </div>
        {!draft && (
          <Button variant="primary" onClick={() => setDraft(emptyDraft())}>
            New schema
          </Button>
        )}
      </div>
      {error && <Alert>{error}</Alert>}
      {draft && (
        <SchemaEditor
          key={draft.id ?? "new"}
          draft={draft}
          onDone={() => {
            setDraft(null);
            load();
          }}
        />
      )}
      {schemas === null ? (
        <p className="text-sm text-ink-muted font-mono">Loading…</p>
      ) : schemas.length === 0 ? (
        !draft && <p className="text-sm text-ink-muted">No schemas yet. Create one here, or save fields from the dashboard.</p>
      ) : (
        <ul className="grid grid-cols-[minmax(0,1fr)] md:grid-cols-[minmax(0,1fr)_minmax(0,1fr)] gap-4">
          {schemas.map((s) => (
            <li key={s.id} className="border border-line bg-white p-5 flex flex-col gap-3">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <h2 className="font-semibold">{s.name}</h2>
                  {s.description && <p className="text-sm text-ink-muted mt-0.5">{s.description}</p>}
                </div>
                <span className="font-mono text-xs text-ink-muted">v{s.version}</span>
              </div>
              <ul className="flex flex-wrap gap-1.5">
                {Object.entries(s.fields).map(([name, spec]) => (
                  <li key={name} className="border border-line px-2 py-0.5 font-mono text-xs">
                    {name} <span className="text-ink-muted">· {spec.type}</span>
                  </li>
                ))}
              </ul>
              <div className="flex gap-2 mt-auto pt-1">
                <Button
                  className="!py-1 text-xs"
                  onClick={() =>
                    setDraft({ id: s.id, name: s.name, description: s.description ?? "", rows: rowsFromFields(s.fields) })
                  }
                >
                  Edit
                </Button>
                <Button variant="danger" className="!py-1 text-xs" onClick={() => remove(s)}>
                  Delete
                </Button>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export default function SchemasPage() {
  return (
    <AppShell>
      <Schemas />
    </AppShell>
  );
}
