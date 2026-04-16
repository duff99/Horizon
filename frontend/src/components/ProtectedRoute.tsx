import { Navigate } from 'react-router-dom';

import { useMe } from '@/hooks/useAuth';

export function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const me = useMe();
  if (me.isLoading) return <div className="p-8">Chargement…</div>;
  if (me.isError || !me.data) return <Navigate to="/connexion" replace />;
  return <>{children}</>;
}
