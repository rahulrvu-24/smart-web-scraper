"use client";

import { useState } from "react";

import { Button } from "@/components/ui";

/** Pretty-printed JSON with light syntax colouring, plus copy and download buttons. */
export default function JsonView({ value, filename }: { value: unknown; filename: string }) {
  const [copied, setCopied] = useState(false);
  const text = JSON.stringify(value, null, 2);

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      // clipboard blocked; the text is still selectable
    }
  };

  const download = () => {
    const url = URL.createObjectURL(new Blob([text], { type: "application/json" }));
    const a = Object.assign(document.createElement("a"), { href: url, download: filename });
    a.click();
    URL.revokeObjectURL(url);
  };

  // Colour keys, strings and literals without a library: split into tokens and style each.
  const tokens = text.split(/("(?:\\.|[^"\\])*"(?:\s*:)?|\b(?:true|false|null)\b|-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)/g);

  return (
    <div className="border border-teal">
      <div className="flex justify-end gap-2 px-3 py-2 border-b border-line bg-paper">
        <Button type="button" onClick={copy} className="!py-1 !px-3 text-xs">
          {copied ? "Copied" : "Copy"}
        </Button>
        <Button type="button" onClick={download} className="!py-1 !px-3 text-xs">
          Download .json
        </Button>
      </div>
      <pre className="p-4 overflow-x-auto text-[0.82rem] leading-relaxed font-mono bg-white">
        {tokens.map((t, i) => {
          if (!t) return null;
          if (t.startsWith("\"") && t.trimEnd().endsWith(":")) return <span key={i}>{t}</span>;
          if (t.startsWith('"') || /^-?\d/.test(t)) return <span key={i} className="text-gold">{t}</span>;
          if (t === "true" || t === "false") return <span key={i} className="text-teal">{t}</span>;
          if (t === "null") return <span key={i} className="text-raw-text">{t}</span>;
          return <span key={i}>{t}</span>;
        })}
      </pre>
    </div>
  );
}
