export function DashboardPage() {
  const kpis = [
    { label: "Solde total", value: "—", hint: "Tous comptes confondus" },
    { label: "Entrées du mois", value: "—", hint: "Crédits catégorisés" },
    { label: "Sorties du mois", value: "—", hint: "Débits catégorisés" },
    { label: "Non catégorisées", value: "—", hint: "À traiter" },
  ];

  return (
    <section className="space-y-6">
      <div>
        <h1 className="text-[22px] font-semibold tracking-tight text-ink">
          Tableau de bord
        </h1>
        <p className="mt-0.5 text-[13px] text-muted-foreground">
          Vue d'ensemble de vos comptes et de votre activité.
        </p>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {kpis.map((k) => (
          <div
            key={k.label}
            className="rounded-xl border border-line-soft bg-panel p-5 shadow-card"
          >
            <div className="text-[11px] font-semibold uppercase tracking-wider text-muted-foreground">
              {k.label}
            </div>
            <div className="mt-2 font-mono text-[24px] font-semibold tabular-nums text-ink">
              {k.value}
            </div>
            <div className="mt-1 text-[12px] text-muted-foreground">{k.hint}</div>
          </div>
        ))}
      </div>

      <div className="rounded-xl border border-line-soft bg-panel p-10 text-center shadow-card">
        <div className="text-[13px] text-muted-foreground">
          Les graphiques détaillés (tendance, répartition, prévisionnel) seront
          ajoutés dans le Plan 3.
        </div>
      </div>
    </section>
  );
}
