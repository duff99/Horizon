import type { DocSectionData } from "@/content/documentation";

/**
 * DocSection — bloc éditorial pour une page documentée.
 *
 * Structure : ancre · titre h2 · sous-titre · bloc « Ce que vous voyez » ·
 * bloc « Ce que vous pouvez faire » · bloc « Astuces » (optionnel).
 * Pas de carte boîte-en-boîte : on groupe par lignes de séparation pour un feel
 * éditorial. `scroll-mt-8` décale l'ancre sous un éventuel header sticky.
 */
export function DocSection({ data }: { data: DocSectionData }) {
  return (
    <section
      id={data.id}
      aria-labelledby={`${data.id}-title`}
      className="scroll-mt-10 border-t border-line-soft pt-10 first:border-t-0 first:pt-0"
    >
      <header className="max-w-[65ch]">
        <h2
          id={`${data.id}-title`}
          className="text-[22px] font-semibold tracking-tight text-ink"
        >
          {data.title}
        </h2>
        <p className="mt-1.5 text-[14px] leading-relaxed text-muted-foreground">
          {data.subtitle}
        </p>
      </header>

      <DocBlock label="Ce que vous voyez" items={data.sees} />
      <DocBlock label="Ce que vous pouvez faire" items={data.does} accent />
      {data.tips && data.tips.length > 0 && (
        <DocBlock label="Astuces" items={data.tips} tone="muted" />
      )}
    </section>
  );
}

function DocBlock({
  label,
  items,
  accent = false,
  tone = "default",
}: {
  label: string;
  items: string[];
  accent?: boolean;
  tone?: "default" | "muted";
}) {
  return (
    <div className="mt-7 max-w-[65ch]">
      <div className="flex items-center gap-2">
        <span
          aria-hidden
          className={
            "inline-block h-1.5 w-1.5 rounded-full " +
            (accent ? "bg-accent" : tone === "muted" ? "bg-amber-500" : "bg-ink")
          }
        />
        <h3 className="text-[11px] font-semibold uppercase tracking-[0.14em] text-ink-2">
          {label}
        </h3>
      </div>
      <ul className="mt-3 space-y-2.5">
        {items.map((item, idx) => (
          <li
            key={idx}
            className={
              "relative pl-5 text-[14px] leading-relaxed " +
              (tone === "muted" ? "text-ink-2" : "text-ink")
            }
          >
            <span
              aria-hidden
              className="absolute left-0 top-[0.7em] h-px w-3 bg-line"
            />
            {item}
          </li>
        ))}
      </ul>
    </div>
  );
}
