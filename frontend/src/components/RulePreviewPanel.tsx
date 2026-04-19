import type { RulePreviewResponse } from "@/api/rules";

export function RulePreviewPanel({ preview }: { preview: RulePreviewResponse | null }) {
  if (!preview) return null;
  return (
    <div className="border rounded p-3 mt-4 bg-muted/50">
      <p className="font-medium">
        {preview.matching_count} transaction{preview.matching_count > 1 ? "s" : ""}{" "}
        correspond{preview.matching_count > 1 ? "ent" : ""} à cette règle.
      </p>
      {preview.sample.length > 0 && (
        <ul className="mt-2 text-sm space-y-1 max-h-64 overflow-y-auto">
          {preview.sample.map((s) => (
            <li key={s.id} className="flex justify-between">
              <span>{s.operation_date} — {s.label}</span>
              <span className="font-mono">{s.amount} €</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
