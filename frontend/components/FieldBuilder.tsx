"use client";

import { FIELD_TYPES, type FieldType } from "@/lib/api";
import { newRow, toFieldName, type FieldRow } from "@/lib/fields";
import { Button, inputClass } from "@/components/ui";

const TYPE_LABEL: Record<FieldType, string> = {
  string: "text",
  number: "number",
  integer: "whole number",
  boolean: "yes / no",
  string_list: "list of text",
};

/** Editable list of fields to extract: name, type and an optional hint for the LLM. */
export default function FieldBuilder({ rows, onChange }: { rows: FieldRow[]; onChange: (rows: FieldRow[]) => void }) {
  const update = (key: number, patch: Partial<FieldRow>) =>
    onChange(rows.map((r) => (r.key === key ? { ...r, ...patch } : r)));

  return (
    <div>
      <div className="hidden md:grid grid-cols-[minmax(0,1fr)_9rem_minmax(0,1.6fr)_2rem] gap-2 text-xs font-semibold uppercase tracking-wide text-ink-muted mb-1.5">
        <span>Field name</span>
        <span>Type</span>
        <span>Hint for the model (optional)</span>
        <span />
      </div>
      <div className="flex flex-col gap-2">
        {rows.map((row) => (
          <div key={row.key} className="grid grid-cols-[minmax(0,1fr)_8rem_2rem] md:grid-cols-[minmax(0,1fr)_9rem_minmax(0,1.6fr)_2rem] gap-2 items-center">
            <input
              aria-label="Field name"
              className={`${inputClass} font-mono`}
              placeholder="price"
              value={row.name}
              onChange={(e) => update(row.key, { name: toFieldName(e.target.value) })}
            />
            <select
              aria-label="Field type"
              className={inputClass}
              value={row.type}
              onChange={(e) => update(row.key, { type: e.target.value as FieldType })}
            >
              {FIELD_TYPES.map((t) => (
                <option key={t} value={t}>
                  {TYPE_LABEL[t]}
                </option>
              ))}
            </select>
            <input
              aria-label="Hint"
              className={`${inputClass} col-span-2 md:col-span-1 row-start-2 md:row-start-auto`}
              placeholder="e.g. price in the page's currency"
              value={row.description}
              maxLength={300}
              onChange={(e) => update(row.key, { description: e.target.value })}
            />
            <button
              type="button"
              aria-label="Remove field"
              className="h-9 text-ink-muted hover:text-raw-tag disabled:opacity-30 row-start-1 col-start-3 md:col-start-auto md:row-start-auto"
              disabled={rows.length === 1}
              onClick={() => onChange(rows.filter((r) => r.key !== row.key))}
            >
              ✕
            </button>
          </div>
        ))}
      </div>
      <Button type="button" variant="ghost" className="mt-2 !px-0" onClick={() => onChange([...rows, newRow()])} disabled={rows.length >= 25}>
        + Add field
      </Button>
    </div>
  );
}
