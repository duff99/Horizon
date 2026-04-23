import { Link, NavLink } from 'react-router-dom';

import { useLogout, useMe } from '@/hooks/useAuth';
import { cn } from '@/lib/utils';

type Item = {
  to: string;
  label: string;
  icon: JSX.Element;
  adminOnly?: boolean;
};

const icon = (path: JSX.Element) => (
  <svg
    aria-hidden
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth={2}
    strokeLinecap="round"
    strokeLinejoin="round"
    className="h-[18px] w-[18px] shrink-0 opacity-90"
  >
    {path}
  </svg>
);

const pilotage: Item[] = [
  {
    to: '/tableau-de-bord',
    label: 'Tableau de bord',
    icon: icon(
      <>
        <rect x="3" y="3" width="7" height="9" />
        <rect x="14" y="3" width="7" height="5" />
        <rect x="14" y="12" width="7" height="9" />
        <rect x="3" y="16" width="7" height="5" />
      </>,
    ),
  },
  {
    to: '/analyse',
    label: 'Analyse',
    icon: icon(
      <>
        <path d="M3 3v18h18" />
        <polyline points="7 14 11 10 14 13 20 7" />
        <polyline points="15 7 20 7 20 12" />
      </>,
    ),
  },
  {
    to: '/transactions',
    label: 'Transactions',
    icon: icon(
      <>
        <path d="M3 6h18M3 12h18M3 18h18" />
      </>,
    ),
  },
  {
    to: '/engagements',
    label: 'Engagements',
    icon: icon(
      <>
        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
        <polyline points="14 2 14 8 20 8" />
        <line x1="9" y1="13" x2="15" y2="13" />
        <line x1="9" y1="17" x2="13" y2="17" />
      </>,
    ),
  },
  {
    to: '/previsionnel',
    label: 'Prévisionnel',
    icon: icon(
      <>
        <path d="M3 3v18h18" />
        <path d="M7 15l4-4 3 3 5-6" />
      </>,
    ),
  },
  {
    to: '/imports',
    label: 'Imports',
    icon: icon(
      <>
        <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
        <path d="M7 10l5 5 5-5" />
        <path d="M12 15V3" />
      </>,
    ),
  },
];

const config: Item[] = [
  {
    to: '/regles',
    label: 'Règles',
    icon: icon(
      <>
        <circle cx="12" cy="12" r="9" />
        <path d="M12 6v6l3 2" />
      </>,
    ),
  },
  {
    to: '/tiers',
    label: 'Tiers',
    icon: icon(
      <>
        <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
        <circle cx="9" cy="7" r="4" />
        <path d="M23 21v-2a4 4 0 0 0-3-3.87" />
        <path d="M16 3.13a4 4 0 0 1 0 7.75" />
      </>,
    ),
  },
];

const help: Item[] = [
  {
    to: '/documentation',
    label: 'Documentation',
    icon: icon(
      <>
        <path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20" />
        <path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z" />
        <path d="M8 7h8" />
        <path d="M8 11h6" />
      </>,
    ),
  },
];

const admin: Item[] = [
  {
    to: '/administration/utilisateurs',
    label: 'Utilisateurs',
    icon: icon(
      <>
        <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
        <circle cx="12" cy="7" r="4" />
      </>,
    ),
    adminOnly: true,
  },
  {
    to: '/administration/societes',
    label: 'Sociétés',
    icon: icon(
      <>
        <path d="M3 21h18" />
        <path d="M5 21V7l8-4v18" />
        <path d="M19 21V11l-6-4" />
      </>,
    ),
    adminOnly: true,
  },
  {
    to: '/administration/comptes-bancaires',
    label: 'Comptes bancaires',
    icon: icon(
      <>
        <rect x="2" y="5" width="20" height="14" rx="2" />
        <path d="M2 10h20" />
      </>,
    ),
    adminOnly: true,
  },
];

function NavGroup({
  label,
  items,
  isAdmin,
}: {
  label: string;
  items: Item[];
  isAdmin: boolean;
}) {
  const visible = items.filter((i) => !i.adminOnly || isAdmin);
  if (visible.length === 0) return null;
  return (
    <div>
      <div className="px-2 pb-1.5 pt-3.5 text-[10.5px] font-semibold uppercase tracking-wider text-slate-500">
        {label}
      </div>
      <nav className="space-y-0.5">
        {visible.map((i) => (
          <NavLink
            key={i.to}
            to={i.to}
            className={({ isActive }) =>
              cn(
                'flex items-center gap-[11px] rounded-md px-2.5 py-2 text-[13.5px] font-medium text-sidebar-fg hover:bg-white/5 hover:text-white',
                isActive && 'bg-sidebar-hover text-white',
              )
            }
          >
            {({ isActive }) => (
              <>
                <span
                  className={cn(
                    'inline-flex',
                    isActive ? 'text-accent' : 'text-sidebar-fg',
                  )}
                >
                  {i.icon}
                </span>
                <span>{i.label}</span>
              </>
            )}
          </NavLink>
        ))}
      </nav>
    </div>
  );
}

function initials(me: { fullName?: string | null; email?: string | null } | undefined) {
  const src = me?.fullName ?? me?.email ?? '';
  return src
    .split(/[\s@.]+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((s) => s[0]?.toUpperCase() ?? '')
    .join('') || 'H';
}

export function Sidebar() {
  const me = useMe();
  const logout = useLogout();
  const isAdmin = me.data?.role === 'admin';

  return (
    <aside className="sticky top-0 flex h-screen w-[240px] shrink-0 flex-col gap-1 bg-sidebar px-3.5 py-5 text-sidebar-fg">
      <div className="flex items-center gap-2.5 px-2 pb-5 pt-1 text-white">
        <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-gradient-to-br from-accent to-teal-700 text-[14px] font-bold text-[#042f2e]">
          H
        </div>
        <div className="text-[15px] font-bold tracking-tight">horizon</div>
      </div>

      <NavGroup label="Pilotage" items={pilotage} isAdmin={isAdmin} />
      <NavGroup label="Configuration" items={config} isAdmin={isAdmin} />
      <NavGroup label="Administration" items={admin} isAdmin={isAdmin} />
      <NavGroup label="Aide" items={help} isAdmin={isAdmin} />

      <div className="mt-auto flex items-center gap-2 border-t border-white/5 pt-4">
        <Link
          to="/profil"
          aria-label="Mon profil"
          className="flex min-w-0 flex-1 items-center gap-2.5 rounded-md px-1 py-1 -mx-1 transition-colors hover:bg-white/5"
        >
          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-accent to-emerald-700 text-[12px] font-bold text-[#042f2e]">
            {initials(me.data ?? undefined)}
          </div>
          <div className="min-w-0 flex-1">
            <div className="truncate text-[12.5px] font-medium text-white">
              {me.data?.fullName ?? me.data?.email ?? '—'}
            </div>
            <div className="text-[11px] text-slate-500">
              {me.data?.role === 'admin' ? 'admin' : 'utilisateur'}
            </div>
          </div>
        </Link>
        <button
          type="button"
          onClick={() => logout.mutate()}
          className="rounded-md p-1.5 text-slate-400 transition-colors hover:bg-white/5 hover:text-white"
          aria-label="Déconnexion"
        >
          <svg
            aria-hidden
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth={2}
            strokeLinecap="round"
            strokeLinejoin="round"
            className="h-4 w-4"
          >
            <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
            <path d="m16 17 5-5-5-5" />
            <path d="M21 12H9" />
          </svg>
        </button>
      </div>
    </aside>
  );
}
