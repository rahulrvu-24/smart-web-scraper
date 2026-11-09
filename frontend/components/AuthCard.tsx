import Link from "next/link";
import type { ReactNode } from "react";

/** Centered card used by the login and register pages. */
export default function AuthCard({ title, subtitle, children }: { title: string; subtitle: ReactNode; children: ReactNode }) {
  return (
    <main className="min-h-screen flex flex-col">
      <nav className="max-w-6xl w-full mx-auto px-8 py-6">
        <Link href="/" className="font-mono font-semibold text-lg">
          Smart Web Scraper
        </Link>
      </nav>
      <div className="flex-1 flex items-start justify-center px-6 pt-12 pb-24">
        <div className="w-full max-w-sm">
          <h1 className="text-3xl font-bold tracking-tight">{title}</h1>
          <p className="text-ink-muted mt-2 text-sm">{subtitle}</p>
          <div className="mt-8">{children}</div>
        </div>
      </div>
    </main>
  );
}
