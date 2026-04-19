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
  const [amountOp] = useState<RuleAmountOperator | "">(
    (init?.amount_operator as RuleAmountOperator) ?? ""
  );
  const [amountVal] = useState(init?.amount_value ?? "");
  const [amountVal2] = useState(init?.amount_value2 ?? "");
  const [counterpartyId] = useState<number | null>(init?.counterparty_id ?? null);
  const [bankAccountId] = useState<number | null>(init?.bank_account_id ?? null);
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

  async function handleSubmit(applyAfter: boolean) {
    if (!categoryId) return;
    await props.onSubmit(buildPayload(), applyAfter);
  }

  return (
    <form className="space-y-4" onSubmit={(e) => { e.preventDefault(); handleSubmit(false); }}>
      <div>
        <Label htmlFor="rule-name">Nom</Label>
        <Input id="rule-name" value={name} onChange={(e) => setName(e.target.value)} />
      </div>

      <div>
        <Label htmlFor="rule-priority">Priorité</Label>
        <Input
          id="rule-priority" type="number"
          value={priority}
          onChange={(e) => setPriority(Number(e.target.value))}
        />
      </div>

      <div>
        <Label>Scope</Label>
        <Select value={entityId != null ? String(entityId) : "__global__"} onValueChange={(v) =>
          setEntityId(v === "__global__" ? null : Number(v))
        }>
          <SelectTrigger><SelectValue placeholder="Globale" /></SelectTrigger>
          <SelectContent>
            <SelectItem value="__global__">Globale (toutes entités)</SelectItem>
            {props.entities.map((e) => (
              <SelectItem key={e.id} value={String(e.id)}>{e.name}</SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <fieldset className="border p-3 rounded">
        <legend className="px-2 text-sm">Filtre libellé</legend>
        <div className="flex gap-2">
          <Select value={labelOp} onValueChange={(v) => setLabelOp(v as RuleLabelOperator)}>
            <SelectTrigger className="w-[180px]"><SelectValue /></SelectTrigger>
            <SelectContent>
              <SelectItem value="CONTAINS">contient</SelectItem>
              <SelectItem value="STARTS_WITH">commence par</SelectItem>
              <SelectItem value="ENDS_WITH">finit par</SelectItem>
              <SelectItem value="EQUALS">égal à</SelectItem>
            </SelectContent>
          </Select>
          <Input
            aria-label="Libellé contient"
            placeholder="ex. URSSAF (sera normalisé)"
            value={labelValue}
            onChange={(e) => setLabelValue(e.target.value)}
          />
        </div>
      </fieldset>

      <fieldset className="border p-3 rounded">
        <legend className="px-2 text-sm">Sens</legend>
        <Select value={direction} onValueChange={(v) => setDirection(v as RuleDirection)}>
          <SelectTrigger><SelectValue /></SelectTrigger>
          <SelectContent>
            <SelectItem value="ANY">Tous</SelectItem>
            <SelectItem value="CREDIT">Crédits uniquement</SelectItem>
            <SelectItem value="DEBIT">Débits uniquement</SelectItem>
          </SelectContent>
        </Select>
      </fieldset>

      <div>
        <Label>Catégorie cible</Label>
        <CategoryCombobox
          categories={props.categories}
          value={categoryId}
          onChange={setCategoryId}
        />
      </div>

      <RulePreviewPanel preview={preview} />

      <div className="flex gap-2 justify-end">
        <Button variant="ghost" type="button" onClick={props.onCancel}>Annuler</Button>
        <Button variant="outline" type="button" onClick={handlePreview}>Aperçu</Button>
        <Button type="button" onClick={() => handleSubmit(false)}>Créer</Button>
        <Button type="button" onClick={() => handleSubmit(true)}>Créer et appliquer</Button>
      </div>
    </form>
  );
}
