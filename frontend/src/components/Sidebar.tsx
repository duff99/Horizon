import { NavLink } from 'react-router-dom';

import { Button } from '@/components/ui/button';
import { useLogout, useMe } from '@/hooks/useAuth';

const items = [
  { to: '/tableau-de-bord', label: 'Tableau de bord', adminOnly: false },
  { to: '/administration/utilisateurs', label: 'Utilisateurs', adminOnly: true },
  { to: '/administration/societes', label: 'Sociétés', adminOnly: true },
  {
    to: '/administration/comptes-bancaires',
    label: 'Comptes bancaires',
    adminOnly: true,
  },
];

export function Sidebar() {
  const me = useMe();
  const logout = useLogout();
  const isAdmin = me.data?.role === 'admin';

  return (
    <aside className="w-64 min-h-screen bg-white border-r border-slate-200 p-4 flex flex-col">
      <h2 className="text-xl font-bold mb-6">Trésorerie</h2>
      <nav className="flex-1 space-y-1">
        {items
          .filter((i) => !i.adminOnly || isAdmin)
          .map((i) => (
            <NavLink
              key={i.to}
              to={i.to}
              className={({ isActive }) =>
                `block px-3 py-2 rounded hover:bg-slate-100 ${
                  isActive ? 'bg-slate-100 font-medium' : ''
                }`
              }
            >
              {i.label}
            </NavLink>
          ))}
      </nav>
      <div className="pt-4 border-t border-slate-200 text-sm text-slate-600">
        <p className="mb-2">{me.data?.fullName ?? me.data?.email}</p>
        <Button variant="outline" className="w-full" onClick={() => logout.mutate()}>
          Déconnexion
        </Button>
      </div>
    </aside>
  );
}
