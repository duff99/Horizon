import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { RouterProvider } from 'react-router-dom';

import './index.css';
import { initErrorReporter } from './lib/errorReporter';
import { router } from './router';

// Capture window.onerror, unhandledrejection et console.error → backend.
// Doit être appelé avant le render pour ne rien rater au boot.
initErrorReporter();

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60_000,  // 5 min
      gcTime: 10 * 60_000,    // 10 min
      refetchOnWindowFocus: false,
      retry: 1,
    },
  },
});

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <RouterProvider router={router} />
    </QueryClientProvider>
  </StrictMode>
);
