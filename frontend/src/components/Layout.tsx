import { Outlet, useLocation } from 'react-router-dom';

import { HelpButton } from '@/components/help/HelpButton';
import { HelpProvider } from '@/components/help/HelpProvider';
import { Sidebar } from '@/components/Sidebar';

// Routes qui exploitent toute la largeur disponible (tableaux denses).
// Les autres restent dans un container max-w-[1320px] pour le confort
// de lecture (pages éditoriales, formulaires).
const FULL_WIDTH_PREFIXES = ['/previsionnel'];

function isFullWidthRoute(pathname: string): boolean {
  return FULL_WIDTH_PREFIXES.some((p) => pathname.startsWith(p));
}

export function Layout() {
  const { pathname } = useLocation();
  const fullWidth = isFullWidthRoute(pathname);

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
              fullWidth
                ? 'w-full px-6 py-6'
                : 'mx-auto w-full max-w-[1320px] px-8 py-6'
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
