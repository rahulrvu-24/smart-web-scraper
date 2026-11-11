"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import type { ReactNode } from "react";

import { api } from "@/lib/api";
import { useCurrentUser } from "@/lib/auth";

const NAV = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/schemas", label: "Schemas" },
  { href: "/activity", label: "Activity" },
  { href: "/status", label: "Status" },
];

/** Layout for logged-in pages: header + nav, and nothing rendered until the user is known. */
export default function AppShell({ children }: { children: ReactNode }) {
  const { user, error } = useCurrentUser();
  const pathname = usePathname();

  return (
    <div className="min-h-screen">
      <header className="border-b border-line bg-paper">
        <div className="max-w-6xl mx-auto px-6 h-14 flex items-center justify-between gap-6">
          <div className="flex items-center gap-8">
            <Link href="/dashboard" className="font-mono font-semibold">
              Smart Web Scraper
            </Link>
            <nav className="hidden sm:flex items-center gap-6 text-sm">
              {NAV.map((item) => (
                <Link
                  key={item.href}
                  href={item.href}
                  className={pathname.startsWith(item.href) ? "text-ink font-semibold" : "text-ink-muted hover:text-ink"}
                >
                  {item.label}
                </Link>
              ))}
            </nav>
          </div>
          <div className="flex items-center gap-4 text-sm">
            {user && <span className="hidden md:inline text-ink-muted font-mono text-xs">{user.email}</span>}
            <button onClick={() => api.logout()} className="text-ink-muted hover:text-ink">
              Log out
            </button>
          </div>
        </div>
        <nav className="sm:hidden flex gap-6 px-6 pb-3 text-sm">
          {NAV.map((item) => (
            <Link key={item.href} href={item.href} className="text-ink-muted hover:text-ink">
              {item.label}
            </Link>
          ))}
        </nav>
      </header>
      <main className="max-w-6xl mx-auto px-6 py-8">
        {error ? (
          <p className="text-raw-tag text-sm">{error}</p>
        ) : user ? (
          children
        ) : (
          <p className="text-ink-muted text-sm font-mono">Loading…</p>
        )}
      </main>
    </div>
  );
}
