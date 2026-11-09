"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState, type FormEvent } from "react";

import AuthCard from "@/components/AuthCard";
import { Alert, Button, Input, Label } from "@/components/ui";
import { api } from "@/lib/api";

export default function RegisterPage() {
  const router = useRouter();
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await api.register(email, password, fullName.trim() || undefined);
      await api.login(email, password); // sign straight in after registering
      router.push("/dashboard");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Registration failed");
      setBusy(false);
    }
  };

  return (
    <AuthCard
      title="Create an account"
      subtitle={
        <>
          Already have one?{" "}
          <Link href="/login" className="text-ink underline">
            Log in
          </Link>
        </>
      }
    >
      <form onSubmit={submit} className="flex flex-col gap-4">
        <div>
          <Label htmlFor="name">Name (optional)</Label>
          <Input id="name" autoComplete="name" maxLength={100} value={fullName} onChange={(e) => setFullName(e.target.value)} />
        </div>
        <div>
          <Label htmlFor="email">Email</Label>
          <Input id="email" type="email" autoComplete="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
        </div>
        <div>
          <Label htmlFor="password">Password</Label>
          <Input
            id="password"
            type="password"
            autoComplete="new-password"
            required
            minLength={8}
            maxLength={128}
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
          <p className="text-xs text-ink-muted mt-1.5">At least 8 characters.</p>
        </div>
        {error && <Alert>{error}</Alert>}
        <Button type="submit" variant="primary" disabled={busy}>
          {busy ? "Creating account…" : "Create account"}
        </Button>
      </form>
    </AuthCard>
  );
}
