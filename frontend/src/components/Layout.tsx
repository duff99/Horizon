import { Outlet, useLocation } from 'react-router-dom';

import { HelpButton } from '@/components/help/HelpButton';
import { HelpProvider } from '@/components/help/HelpProvider';
import { Sidebar } from '@/components/Sidebar';

// Pages éditoriales / lecture longue : on conserve un container plus
// étroit pour le confort de lecture. Toutes les autres pages
// exploitent toute la largeur disponible.
const NARROW_PREFIXES = ['/documentation'];

function isNarrowRoute(pathname: string): boolean {
  return NARROW_PREFIXES.some((p) => pathname.startsWith(p));
}

export function Layout() {
  const { pathname } = useLocation();
  const narrow = isNarrowRoute(pathname);

  return (
    <HelpProvider>
      <div className="flex min-h-screen bg-canvas">
        <Sidebar />
        {/*
         * `overflow-x-clip` (et non `overflow-x-hidden`) car ce dernier
         * crée un contexte qui casse `position: sticky` chez les enfants
         * (notamment le sommaire de la page Documentation).
         */}
        <main className="flex-1 overflow-x-clip">
          <div
            className={
              narrow
                ? 'mx-auto w-full max-w-[1100px] px-8 py-6'
                : 'w-full px-6 py-6'
            }
          >
            <Outlet />
          </div>
        </main>
      </div>
      <HelpButton />
    </HelpProvider>
  );
}
