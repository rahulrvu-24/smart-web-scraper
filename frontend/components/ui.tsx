import type { ButtonHTMLAttributes, InputHTMLAttributes, ReactNode, SelectHTMLAttributes, TextareaHTMLAttributes } from "react";

import type { JobStatus } from "@/lib/api";

const cx = (...parts: (string | false | null | undefined)[]) => parts.filter(Boolean).join(" ");

export function Button({
  variant = "secondary",
  className,
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: "primary" | "secondary" | "danger" | "ghost" }) {
  return (
    <button
      {...props}
      className={cx(
        "px-4 py-2 text-sm font-semibold transition-colors disabled:opacity-50 disabled:cursor-not-allowed",
        variant === "primary" && "bg-gold text-paper hover:bg-ink",
        variant === "secondary" && "border border-line bg-white hover:border-ink",
        variant === "danger" && "border border-line bg-white text-raw-tag hover:border-raw-tag",
        variant === "ghost" && "text-ink-muted hover:text-ink px-2",
        className,
      )}
    />
  );
}

export const inputClass =
  "w-full min-w-0 border border-line bg-white px-3 py-2 text-sm focus:outline-none focus:border-ink placeholder:text-raw-text";

export function Input({ className, ...props }: InputHTMLAttributes<HTMLInputElement>) {
  return <input {...props} className={cx(inputClass, className)} />;
}

export function Select({ className, ...props }: SelectHTMLAttributes<HTMLSelectElement>) {
  return <select {...props} className={cx(inputClass, "pr-8", className)} />;
}

export function Textarea({ className, ...props }: TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return <textarea {...props} className={cx(inputClass, className)} />;
}

export function Label({ children, htmlFor }: { children: ReactNode; htmlFor?: string }) {
  return (
    <label htmlFor={htmlFor} className="block text-xs font-semibold uppercase tracking-wide text-ink-muted mb-1.5">
      {children}
    </label>
  );
}

export function Panel({ title, action, children }: { title?: string; action?: ReactNode; children: ReactNode }) {
  return (
    <section className="border border-line bg-white">
      {title && (
        <div className="flex items-center justify-between px-5 py-3 border-b border-line">
          <h2 className="font-semibold">{title}</h2>
          {action}
        </div>
      )}
      <div className="p-5">{children}</div>
    </section>
  );
}

export function Alert({ children, tone = "error" }: { children: ReactNode; tone?: "error" | "info" }) {
  return (
    <div
      role={tone === "error" ? "alert" : "status"}
      className={cx(
        "border-l-2 px-4 py-3 text-sm",
        tone === "error" ? "border-raw-tag bg-raw-tag/5 text-ink" : "border-teal bg-teal/5 text-ink",
      )}
    >
      {children}
    </div>
  );
}

const STATUS_STYLE: Record<JobStatus, { dot: string; text: string; label: string }> = {
  queued: { dot: "bg-gold", text: "text-gold", label: "queued" },
  running: { dot: "bg-gold animate-pulse", text: "text-gold", label: "running" },
  succeeded: { dot: "bg-teal", text: "text-teal", label: "succeeded" },
  failed: { dot: "bg-raw-tag", text: "text-raw-tag", label: "failed" },
};

export function StatusBadge({ status }: { status: JobStatus }) {
  const s = STATUS_STYLE[status];
  return (
    <span className={cx("inline-flex items-center gap-2 font-mono text-xs", s.text)}>
      <span aria-hidden className={cx("w-2 h-2", s.dot)} />
      {s.label}
    </span>
  );
}
