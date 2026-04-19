import { useState } from 'react';

import { ApiError } from '@/api/client';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { useLogin } from '@/hooks/useAuth';

export function LoginPage() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const login = useLogin();

  return (
    <div className="relative flex min-h-screen items-center justify-center bg-canvas px-4 py-10">
      {/* Subtle decorative glow */}
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 overflow-hidden"
      >
        <div className="absolute -top-40 left-1/2 h-[420px] w-[680px] -translate-x-1/2 rounded-full bg-accent/10 blur-3xl" />
      </div>

      <div className="relative w-full max-w-[380px]">
        {/* Brand header */}
        <div className="mb-6 flex flex-col items-center">
          <div className="mb-3 flex h-12 w-12 items-center justify-center rounded-xl bg-gradient-to-br from-accent to-teal-700 text-lg font-bold text-[#042f2e] shadow-sm">
            H
          </div>
          <div className="text-[20px] font-bold tracking-tight text-ink">
            horizon
          </div>
          <div className="mt-0.5 text-[12.5px] text-muted-foreground">
            Gestion financière
          </div>
        </div>

        <form
          className="space-y-4 rounded-xl border border-line-soft bg-panel p-7 shadow-card"
          onSubmit={(e) => {
            e.preventDefault();
            login.mutate({ email, password });
          }}
        >
          <div>
            <h1 className="text-[17px] font-semibold tracking-tight text-ink">
              Connexion
            </h1>
            <p className="mt-0.5 text-[12.5px] text-muted-foreground">
              Accédez à votre tableau de bord.
            </p>
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="email" className="text-[12.5px] font-medium text-ink-2">
              Email
            </Label>
            <Input
              id="email"
              type="email"
              autoComplete="email"
              placeholder="vous@exemple.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="password" className="text-[12.5px] font-medium text-ink-2">
              Mot de passe
            </Label>
            <Input
              id="password"
              type="password"
              autoComplete="current-password"
              placeholder="••••••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </div>

          {login.error instanceof ApiError && (
            <div
              role="alert"
              className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-[12.5px] text-red-800"
            >
              {login.error.detail}
            </div>
          )}

          <Button type="submit" className="w-full" disabled={login.isPending}>
            {login.isPending ? 'Connexion…' : 'Se connecter'}
          </Button>
        </form>

        <p className="mt-4 text-center text-[11.5px] text-muted-foreground">
          © {new Date().getFullYear()} Horizon · ACREED
        </p>
      </div>
    </div>
  );
}
