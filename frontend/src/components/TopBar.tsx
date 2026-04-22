import { Link } from 'react-router-dom';

import { EntitySelector } from '@/components/EntitySelector';
import { useLogout, useMe } from '@/hooks/useAuth';

export function TopBar() {
  const me = useMe();
  const logout = useLogout();
  const label = me.data?.fullName ?? me.data?.email ?? '—';

  return (
    <div className="flex h-14 items-center justify-between border-b border-border bg-surface px-8">
      <div className="flex items-center gap-3">
        <EntitySelector />
      </div>

      <div className="flex items-center gap-4">
        <span className="text-sm text-slate-600" data-testid="topbar-user">
          {label}
        </span>
        <Link
          to="/profil"
          className="rounded-md px-2 py-1 text-sm text-slate-600 hover:bg-slate-100 hover:text-slate-900"
        >
          Mon profil
        </Link>
        <button
          type="button"
          onClick={() => logout.mutate()}
          className="rounded-md px-2 py-1 text-sm text-slate-600 hover:bg-slate-100 hover:text-slate-900"
        >
          Se déconnecter
        </button>
      </div>
    </div>
  );
}
