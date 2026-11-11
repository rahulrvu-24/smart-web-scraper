import type { Fields, FieldType } from "@/lib/api";

export type FieldRow = { key: number; name: string; type: FieldType; description: string };

const NAME_RE = /^[a-z][a-z0-9_]{0,49}$/;
let nextKey = 1;

export const newRow = (name = "", type: FieldType = "string", description = ""): FieldRow => ({
  key: nextKey++,
  name,
  type,
  description,
});

export const rowsFromFields = (fields: Fields): FieldRow[] =>
  Object.entries(fields).map(([name, spec]) => newRow(name, spec.type, spec.description ?? ""));

/** Turns editor rows into the API's {name: {type, description}} shape, or explains what's wrong. */
export function fieldsFromRows(rows: FieldRow[]): { fields: Fields; error: string | null } {
  const fields: Fields = {};
  const filled = rows.filter((r) => r.name.trim() || r.description.trim());
  if (filled.length === 0) return { fields, error: "Add at least one field to extract." };
  for (const row of filled) {
    const name = row.name.trim();
    if (!NAME_RE.test(name)) {
      return {
        fields,
        error: `"${name || "(empty)"}" isn't a valid field name. Use lowercase letters, digits and _, starting with a letter.`,
      };
    }
    if (name in fields) return { fields, error: `The field "${name}" appears twice.` };
    fields[name] = { type: row.type, description: row.description.trim() };
  }
  return { fields, error: null };
}

export const toFieldName = (raw: string) =>
  raw
    .toLowerCase()
    .replace(/[^a-z0-9_]+/g, "_")
    .replace(/^_+/, "")
    .slice(0, 50);

type Preset = { label: string; url: string; fields: [string, FieldType, string][] };

export const PRESETS: Preset[] = [
  {
    label: "Product page",
    url: "https://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html",
    fields: [
      ["title", "string", "Product name"],
      ["price", "number", "Current price as a number"],
      ["currency", "string", "Currency code or symbol, e.g. GBP or £"],
      ["in_stock", "boolean", "Whether it can be bought now"],
      ["stock_count", "integer", "Number of items available, if shown"],
      ["rating", "string", "Star rating as shown on the page"],
    ],
  },
  {
    label: "Article",
    url: "https://en.wikipedia.org/wiki/Web_scraping",
    fields: [
      ["headline", "string", "The article's main title"],
      ["summary", "string", "Two or three sentences summarising the article"],
      ["topics", "string_list", "Main topics covered"],
      ["related_techniques", "string_list", "Techniques or tools mentioned"],
    ],
  },
  {
    label: "Quotes",
    url: "https://quotes.toscrape.com/",
    fields: [
      ["quotes", "string_list", "Every quote's text on the page"],
      ["authors", "string_list", "Authors in the same order as the quotes"],
      ["top_tags", "string_list", "Tags listed under 'Top Ten tags'"],
    ],
  },
];
