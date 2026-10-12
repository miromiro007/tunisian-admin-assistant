import { useState } from "react";
import { ChevronDown } from "lucide-react";
import { motion } from "framer-motion";
import type { Source } from "../types";
import { useLang } from "../i18n";

interface SourceCardProps {
  source: Source;
  highlighted?: boolean;
  elementId: string;
}

export function SourceCard({ source, highlighted, elementId }: SourceCardProps) {
  const { t } = useLang();
  const [open, setOpen] = useState(source.cited);

  return (
    <div
      id={elementId}
      className={`rounded-xl border bg-(--color-surface) p-3 transition-colors ${
        highlighted ? "border-accent-500 ring-2 ring-accent-500/30" : "border-(--color-border)"
      }`}
    >
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center justify-between gap-2 text-left"
        aria-expanded={open}
      >
        <div className="min-w-0">
          <p className="truncate text-sm font-medium text-(--color-text)" dir="auto">
            {source.law_title ?? source.document}
          </p>
          <p className="text-xs text-(--color-text-muted)">
            {[
              source.article ? `Art. ${source.article}` : null,
              source.page != null ? `p.${source.page}` : null,
            ]
              .filter(Boolean)
              .join(" · ")}
          </p>
        </div>
        <ChevronDown
          size={16}
          className={`shrink-0 text-(--color-text-muted) transition-transform ${open ? "rotate-180" : ""}`}
        />
      </button>

      <motion.div
        initial={false}
        animate={{ height: open ? "auto" : 0, opacity: open ? 1 : 0 }}
        className="overflow-hidden"
      >
        <p className="bidi-plaintext mt-2 text-sm text-(--color-text-muted)" dir="auto">
          {source.excerpt}
        </p>
        <div className="mt-2 flex items-center gap-2">
          <span className="text-xs text-(--color-text-muted)">{t("sources.score")}</span>
          <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-(--color-surface-muted)">
            <div
              className="h-full rounded-full bg-accent-500"
              style={{ width: `${Math.round(Math.min(1, Math.max(0, source.score)) * 100)}%` }}
            />
          </div>
        </div>
      </motion.div>
    </div>
  );
}
