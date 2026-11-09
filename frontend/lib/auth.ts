"use client";

import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { api, ApiError, LOGOUT_EVENT, tokenStore, type User } from "@/lib/api";

/** Loads the logged-in user, or sends the visitor to /login if there isn't one. */
export function useCurrentUser(): { user: User | null; error: string | null } {
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    const toLogin = () => router.replace("/login");
    window.addEventListener(LOGOUT_EVENT, toLogin);
    if (!tokenStore.get()) {
      toLogin();
    } else {
      api
        .me()
        .then((u) => {
          if (active) setUser(u);
        })
        .catch((err) => {
          if (!active) return;
          if (err instanceof ApiError && err.status === 401) toLogin();
          else setError(err instanceof Error ? err.message : "Could not load your account");
        });
    }
    return () => {
      active = false;
      window.removeEventListener(LOGOUT_EVENT, toLogin);
    };
  }, [router]);

  return { user, error };
}
