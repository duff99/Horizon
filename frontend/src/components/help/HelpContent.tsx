import { Link } from "react-router-dom";

import type { DocSectionData } from "@/content/documentation";

type Block = "sees" | "does" | "tips";

const BLOCK_LABELS: Record<Block, string> = {
  sees: "Ce que vous voyez",
  does: "Ce que vous pouvez faire",
  tips: "Astuces",
};

function resolveBlock(section: DocSectionData, kind: Block): string[] {
  const override = section.panel?.[kind];
  if (override !== undefined) return override;
  if (kind === "tips") return section.tips ?? [];
  return section[kind];
}

function isHidden(section: DocSectionData, kind: Block): boolean {
  return section.panel?.hide?.includes(kind) ?? false;
}

export function HelpContent({ section }: { section: DocSectionData }) {
  const summary = section.panel?.summary ?? section.subtitle;

  return (
    <div className="flex h-full flex-col">
      <header className="border-b border-line-soft px-6 pb-5 pt-6">
        <div className="text-[11px] font-semibold uppercase tracking-[0.18em] text-accent">
          Aide sur cette page
        </div>
        <h2 className="mt-2 text-[20px] font-semibold tracking-tight text-ink">
          {section.title}
        </h2>
        <p className="mt-2 text-[13.5px] leading-relaxed text-muted-foreground">
          {summary}
        </p>
      </header>

      <div className="flex-1 overflow-y-auto px-6 py-5">
        {(["sees", "does", "tips"] as const).map((kind) => {
          if (isHidden(section, kind)) return null;
          const items = resolveBlock(section, kind);
          if (items.length === 0) return null;
          return (
            <Block
              key={kind}
              label={BLOCK_LABELS[kind]}
              items={items}
              accent={kind === "does"}
              tone={kind === "tips" ? "muted" : "default"}
            />
          );
        })}
      </div>

      <footer className="border-t border-line-soft px-6 py-4">
        <Link
          to={`/documentation#${section.id}`}
          className="text-[13px] font-medium text-accent hover:underline"
        >
          Voir le guide complet →
        </Link>
      </footer>
    </div>
  );
}

function Block({
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
    <section className="mt-5 first:mt-0">
      <div className="flex items-center gap-2">
        <span
          aria-hidden
          className={
            "inline-block h-1.5 w-1.5 rounded-full " +
            (accent ? "bg-accent" : tone === "muted" ? "bg-amber-500" : "bg-ink")
          }
        />
        <h3 className="text-[10.5px] font-semibold uppercase tracking-[0.14em] text-ink-2">
          {label}
        </h3>
      </div>
      <ul className="mt-2.5 space-y-2">
        {items.map((item, idx) => (
          <li
            key={idx}
            className={
              "relative pl-4 text-[13px] leading-relaxed " +
              (tone === "muted" ? "text-ink-2" : "text-ink")
            }
          >
            <span
              aria-hidden
              className="absolute left-0 top-[0.65em] h-px w-2.5 bg-line"
            />
            {item}
          </li>
        ))}
      </ul>
    </section>
  );
}
