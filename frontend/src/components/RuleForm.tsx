import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "@/components/ui/select";
import type {
  Rule, RuleCreatePayload, RuleDirection, RuleLabelOperator, RuleAmountOperator,
  RulePreviewResponse,
} from "@/api/rules";
import { previewRule } from "@/api/rules";
import { CategoryCombobox, type CategoryOption } from "./CategoryCombobox";
import { RulePreviewPanel } from "./RulePreviewPanel";

interface Props {
  categories: CategoryOption[];
  entities: { id: number; name: string }[];
  counterparties: { id: number; name: string }[];
  bankAccounts: { id: number; name: string; entity_id: number }[];
  initialValue: Rule | null;
  onSubmit: (payload: RuleCreatePayload, applyAfter: boolean) => void | Promise<void>;
  onCancel: () => void;
}

export function RuleForm(props: Props) {
  const init = props.initialValue;
  const [name, setName] = useState(init?.name ?? "");
  const [entityId, setEntityId] = useState<number | null>(init?.entity_id ?? null);
  const [priority, setPriority] = useState<number>(init?.priority ?? 5000);
  const [labelOp, setLabelOp] = useState<RuleLabelOperator | "">(
    (init?.label_operator as RuleLabelOperator) ?? "CONTAINS"
  );
  const [labelValue, setLabelValue] = useState(init?.label_value ?? "");
  const [direction, setDirection] = useState<RuleDirection>(init?.direction ?? "ANY");
  const [amountOp, setAmountOp] = useState<RuleAmountOperator | "">(
    (init?.amount_operator as RuleAmountOperator) ?? ""
  );
  const [amountVal, setAmountVal] = useState(init?.amount_value ?? "");
  const [amountVal2, setAmountVal2] = useState(init?.amount_value2 ?? "");
  const [counterpartyId, setCounterpartyId] = useState<number | null>(init?.counterparty_id ?? null);
  const [bankAccountId, setBankAccountId] = useState<number | null>(init?.bank_account_id ?? null);
  const [categoryId, setCategoryId] = useState<number | null>(init?.category_id ?? null);
  const [preview, setPreview] = useState<RulePreviewResponse | null>(null);

  function buildPayload(): RuleCreatePayload {
    return {
      name,
      entity_id: entityId,
      priority,
      label_operator: labelOp || null,
      label_value: labelValue || null,
      direction,
      amount_operator: amountOp || null,
      amount_value: amountVal || null,
      amount_value2: amountVal2 || null,
      counterparty_id: counterpartyId,
      bank_account_id: bankAccountId,
      category_id: categoryId ?? 0,
    };
  }

  async function handlePreview() {
    const resp = await previewRule(buildPayload());
    setPreview(resp);
  }

  const [submitError, setSubmitError] = useState<string | null>(null);

  async function handleSubmit(applyAfter: boolean) {
    if (!categoryId) {
      setSubmitError("Sélectionnez une catégorie à appliquer avant de créer la règle.");
      return;
    }
    if (!labelValue && !counterpartyId && !bankAccountId && !amountOp && direction === "ANY") {
      setSubmitError("Définissez au moins un filtre (libellé, montant, sens, tiers ou compte).");
      return;
    }
    setSubmitError(null);
    await props.onSubmit(buildPayload(), applyAfter);
  }

  return (
    <form
      className="space-y-4"
      onSubmit={(e) => {
        e.preventDefault();
        handleSubmit(false);
      }}
    >
      {/* Ligne 1 : Nom + Priorité côte à côte */}
      <div className="grid grid-cols-3 gap-3">
        <div className="col-span-2 space-y-1">
          <Label htmlFor="rule-name" className="text-[12.5px] text-ink-2">
            Nom de la règle
          </Label>
          <Input
            id="rule-name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="ex. Loyer"
          />
        </div>
        <div className="space-y-1">
          <Label htmlFor="rule-priority" className="text-[12.5px] text-ink-2">
            Priorité
          </Label>
          <Input
            id="rule-priority"
            type="number"
            value={priority}
            onChange={(e) => setPriority(Number(e.target.value))}
          />
        </div>
      </div>

      {/* Ligne 2 : Scope (société) + Sens côte à côte */}
      <div className="grid grid-cols-2 gap-3">
        <div className="space-y-1">
          <Label className="text-[12.5px] text-ink-2">
            Société concernée
          </Label>
          <Select
            value={entityId != null ? String(entityId) : "__global__"}
            onValueChange={(v) =>
              setEntityId(v === "__global__" ? null : Number(v))
            }
          >
            <SelectTrigger>
              <SelectValue placeholder="Toutes les sociétés" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="__global__">
                Toutes les sociétés (règle globale)
              </SelectItem>
              {props.entities.map((e) => (
                <SelectItem key={e.id} value={String(e.id)}>
                  Uniquement {e.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <p className="text-[11px] text-muted-foreground">
            Choisis « Toutes les sociétés » pour une règle qui s'applique
            partout, ou une société précise pour la limiter à ses comptes
            bancaires.
          </p>
        </div>
        <div className="space-y-1">
          <Label className="text-[12.5px] text-ink-2">Type d'opération</Label>
          <Select
            value={direction}
            onValueChange={(v) => setDirection(v as RuleDirection)}
          >
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="ANY">Toutes</SelectItem>
              <SelectItem value="CREDIT">Encaissements (crédits)</SelectItem>
              <SelectItem value="DEBIT">Décaissements (débits)</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      {/* Ligne 3 : filtre libellé (opérateur + valeur) */}
      <div className="space-y-1">
        <Label className="text-[12.5px] text-ink-2">Filtre sur le libellé</Label>
        <div className="flex gap-2">
          <Select
            value={labelOp}
            onValueChange={(v) => setLabelOp(v as RuleLabelOperator)}
          >
            <SelectTrigger className="w-[150px] shrink-0">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="CONTAINS">contient</SelectItem>
              <SelectItem value="STARTS_WITH">commence par</SelectItem>
              <SelectItem value="ENDS_WITH">finit par</SelectItem>
              <SelectItem value="EQUALS">égal à</SelectItem>
            </SelectContent>
          </Select>
          <Input
            aria-label="Texte du filtre"
            placeholder="ex. URSSAF (sera normalisé)"
            value={labelValue}
            onChange={(e) => setLabelValue(e.target.value)}
          />
        </div>
      </div>

      {/* Ligne 3bis : filtre montant */}
      <div className="space-y-1">
        <Label className="text-[12.5px] text-ink-2">Filtre sur le montant (€)</Label>
        <div className="flex gap-2">
          <Select
            value={amountOp || "__none__"}
            onValueChange={(v) => {
              const next = v === "__none__" ? "" : (v as RuleAmountOperator);
              setAmountOp(next);
              if (next !== "BETWEEN") setAmountVal2("");
              if (next === "") {
                setAmountVal("");
                setAmountVal2("");
              }
            }}
          >
            <SelectTrigger className="w-[180px] shrink-0">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="__none__">Aucun filtre</SelectItem>
              <SelectItem value="EQ">égal à</SelectItem>
              <SelectItem value="NE">différent de</SelectItem>
              <SelectItem value="GT">supérieur à</SelectItem>
              <SelectItem value="LT">inférieur à</SelectItem>
              <SelectItem value="BETWEEN">entre</SelectItem>
            </SelectContent>
          </Select>
          {amountOp && (
            <Input
              aria-label="Montant"
              type="number"
              step="0.01"
              placeholder="ex. 100.00"
              value={amountVal}
              onChange={(e) => setAmountVal(e.target.value)}
            />
          )}
          {amountOp === "BETWEEN" && (
            <Input
              aria-label="Montant max"
              type="number"
              step="0.01"
              placeholder="et"
              value={amountVal2}
              onChange={(e) => setAmountVal2(e.target.value)}
            />
          )}
        </div>
        <p className="text-[11px] text-muted-foreground">
          Le montant est comparé en valeur absolue (signe ignoré).
        </p>
      </div>

      {/* Ligne 3ter : tiers + compte bancaire */}
      <div className="grid grid-cols-2 gap-3">
        <div className="space-y-1">
          <Label className="text-[12.5px] text-ink-2">Tiers (counterparty)</Label>
          <Select
            value={counterpartyId != null ? String(counterpartyId) : "__none__"}
            onValueChange={(v) =>
              setCounterpartyId(v === "__none__" ? null : Number(v))
            }
          >
            <SelectTrigger>
              <SelectValue placeholder="Tous" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="__none__">Tous les tiers</SelectItem>
              {props.counterparties.map((c) => (
                <SelectItem key={c.id} value={String(c.id)}>
                  {c.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-1">
          <Label className="text-[12.5px] text-ink-2">Compte bancaire</Label>
          <Select
            value={bankAccountId != null ? String(bankAccountId) : "__none__"}
            onValueChange={(v) =>
              setBankAccountId(v === "__none__" ? null : Number(v))
            }
          >
            <SelectTrigger>
              <SelectValue placeholder="Tous" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="__none__">Tous les comptes</SelectItem>
              {props.bankAccounts
                .filter((b) => entityId == null || b.entity_id === entityId)
                .map((b) => (
                  <SelectItem key={b.id} value={String(b.id)}>
                    {b.name}
                  </SelectItem>
                ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      {/* Ligne 4 : catégorie cible (sur toute la largeur) */}
      <div className="space-y-1">
        <Label className="text-[12.5px] text-ink-2">Catégorie à appliquer</Label>
        <CategoryCombobox
          categories={props.categories}
          value={categoryId}
          onChange={setCategoryId}
        />
      </div>

      {/* Aperçu : compact si pas encore demandé */}
      {preview ? (
        <RulePreviewPanel preview={preview} />
      ) : (
        <p className="text-[11.5px] text-muted-foreground">
          Cliquez sur Aperçu pour voir combien de transactions existantes
          seraient capturées par cette règle.
        </p>
      )}

      {submitError && (
        <div
          role="alert"
          className="rounded-md border border-rose-200 bg-rose-50 px-3 py-2 text-[12.5px] text-rose-900"
        >
          {submitError}
        </div>
      )}

      <div className="flex flex-wrap items-center justify-end gap-2 border-t border-line-soft pt-3">
        <Button variant="ghost" type="button" onClick={props.onCancel}>
          Annuler
        </Button>
        <Button variant="outline" type="button" onClick={handlePreview}>
          Aperçu
        </Button>
        <Button
          type="button"
          variant="outline"
          onClick={() => handleSubmit(false)}
        >
          Créer
        </Button>
        <Button type="button" onClick={() => handleSubmit(true)}>
          Créer et appliquer
        </Button>
      </div>
    </form>
  );
}
