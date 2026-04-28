/**
 * AnalysePage — tableau de bord d'indicateurs clés et de dérives.
 *
 * 6 widgets orientés KPI, alimentés par `/api/analysis/*`.
 *
 * Politique 2026-04 : la vue cross-entité ("Toutes les sociétés") n'a pas de
 * sens sur cette page (les KPI agrégés mélangeraient des structures de coûts
 * et de revenus indépendantes). On force donc la sélection d'une entité
 * unique : si rien n'est sélectionné au chargement, on prend la première
 * entité accessible (ordre alphabétique côté API).
 */
import { useEffect, useState } from "react";

import { useEntities } from "@/api/entities";
import { EntitySelector } from "@/components/EntitySelector";
import {
  PeriodSelector,
  defaultPeriodValue,
  type PeriodValue,
} from "@/components/PeriodSelector";
import { CategoryDriftTable } from "@/components/analyse/CategoryDriftTable";
import { ClientConcentrationCard } from "@/components/analyse/ClientConcentrationCard";
import { EntitiesComparisonTable } from "@/components/analyse/EntitiesComparisonTable";
import { RunwayCard } from "@/components/analyse/RunwayCard";
import { TopMoversCard } from "@/components/analyse/TopMoversCard";
import { YoYChart } from "@/components/analyse/YoYChart";
import { useEntityFilter } from "@/stores/entityFilter";

export function AnalysePage() {
  const entityId = useEntityFilter((s) => s.entityId);
  const setEntityId = useEntityFilter((s) => s.setEntityId);
  const entitiesQuery = useEntities();
  const entities = entitiesQuery.data ?? [];

  // Auto-sélection de la première entité au chargement si l'utilisateur
  // arrive avec entityId === null (cas "Toutes les sociétés" persisté
  // avant cette fix, ou nouveau user). Évite les 422 backend sur les 5
  // endpoints d'analyse qui exigent entity_id.
  useEffect(() => {
    if (entityId === null && entities.length > 0) {
      setEntityId(entities[0].id);
    }
  }, [entityId, entities, setEntityId]);

  const [period, setPeriod] = useState<PeriodValue>(() =>
    defaultPeriodValue("30d"),
  );

  // Si l'utilisateur n'a accès à aucune entité (cas reader sans grant),
  // on évite de monter les widgets qui partiraient en 422/403 silencieux.
  if (entitiesQuery.isSuccess && entities.length === 0) {
    return (
      <section className="space-y-6">
        <h1 className="text-[22px] font-semibold tracking-tight text-ink">
          Analyse
        </h1>
        <div
          role="alert"
          className="rounded-md bg-amber-50 px-4 py-3 text-[13px] text-amber-900"
        >
          Tu n'as accès à aucune société pour le moment. Demande à un
          administrateur de t'accorder un accès.
        </div>
      </section>
    );
  }

  return (
    <section className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-[22px] font-semibold tracking-tight text-ink">
            Analyse
          </h1>
          <p className="mt-0.5 text-[13px] text-muted-foreground">
            Indicateurs clés, dérives et comparaisons sur les 12 derniers mois.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <EntitySelector allowAll={false} />
          <PeriodSelector value={period} onChange={setPeriod} />
        </div>
      </div>

      <div className="grid grid-cols-12 gap-4">
        <div className="col-span-12">
          <CategoryDriftTable entityId={entityId ?? undefined} />
        </div>
        <div className="col-span-12 md:col-span-6">
          <TopMoversCard entityId={entityId ?? undefined} />
        </div>
        <div className="col-span-12 md:col-span-6">
          <RunwayCard entityId={entityId ?? undefined} />
        </div>
        <div className="col-span-12 md:col-span-8">
          <YoYChart entityId={entityId ?? undefined} />
        </div>
        <div className="col-span-12 md:col-span-4">
          <ClientConcentrationCard entityId={entityId ?? undefined} />
        </div>
        <div className="col-span-12">
          <EntitiesComparisonTable />
        </div>
      </div>

      <details className="rounded-md border border-line-soft bg-panel/40 p-4 text-[12.5px] text-muted-foreground">
        <summary className="cursor-pointer font-medium text-ink">
          Lexique des sigles utilisés sur cette page
        </summary>
        <dl className="mt-3 space-y-2.5">
          <div>
            <dt className="font-semibold text-ink">
              Runway (autonomie de trésorerie)
            </dt>
            <dd>
              Nombre de mois pendant lesquels la société peut tenir à son
              rythme actuel de consommation de cash. Plus c'est élevé, plus
              la société est à l'aise. Rouge si moins de 6 mois.
            </dd>
          </div>
          <div>
            <dt className="font-semibold text-ink">
              Burn rate (consommation mensuelle)
            </dt>
            <dd>
              Différence moyenne entre les sorties et les entrées de cash
              sur les 3 derniers mois. Un burn rate négatif signifie que la
              société consomme sa trésorerie chaque mois.
            </dd>
          </div>
          <div>
            <dt className="font-semibold text-ink">
              YoY (Year over Year, année sur année)
            </dt>
            <dd>
              Comparaison d'un indicateur entre une période et la même
              période l'année précédente. Permet d'isoler la tendance de
              fond des effets saisonniers.
            </dd>
          </div>
          <div>
            <dt className="font-semibold text-ink">
              HHI (Herfindahl-Hirschman Index)
            </dt>
            <dd>
              Mesure standard de concentration. Somme des carrés des parts
              de chaque client dans le chiffre d'affaires. Varie de 0
              (parfaitement diversifié) à 10 000 (un seul client). Repères :
              moins de 1500 = faible, 1500 à 2500 = modérée, plus de 2500 =
              forte.
            </dd>
          </div>
        </dl>
      </details>
    </section>
  );
}
