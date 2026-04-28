import { Outlet } from 'react-router-dom';

import { HelpButton } from '@/components/help/HelpButton';
import { HelpProvider } from '@/components/help/HelpProvider';
import { Sidebar } from '@/components/Sidebar';

export function Layout() {
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
          <div className="mx-auto w-full max-w-[1320px] px-8 py-6">
            <Outlet />
          </div>
        </main>
      </div>
      <HelpButton />
    </HelpProvider>
  );
}
