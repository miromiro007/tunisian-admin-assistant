import { useState } from "react";
import { ChevronDown } from "lucide-react";
import { motion } from "framer-motion";
import type { Source } from "../types";
import { useLang } from "../i18n";

const EXCERPT_COLLAPSE_LENGTH = 300;

interface SourceCardProps {
  source: Source;
  highlighted?: boolean;
  elementId: string;
}

export function SourceCard({ source, highlighted, elementId }: SourceCardProps) {
  const { t } = useLang();
  const [open, setOpen] = useState(source.cited);
  const [fullExcerptShown, setFullExcerptShown] = useState(false);
  const [prevHighlighted, setPrevHighlighted] = useState(highlighted);

  // A citation-chip click expands the card and keeps it open after the highlight fades.
  if (highlighted !== prevHighlighted) {
    setPrevHighlighted(highlighted);
    if (highlighted) setOpen(true);
  }

  const sourceDir = source.language === "ar" ? "rtl" : "ltr";
  const isExcerptLong = source.excerpt.length > EXCERPT_COLLAPSE_LENGTH;
  const displayedExcerpt =
    isExcerptLong && !fullExcerptShown
      ? `${source.excerpt.slice(0, EXCERPT_COLLAPSE_LENGTH)}…`
      : source.excerpt;
  const scorePct = Math.round(Math.min(1, Math.max(0, source.score)) * 100);
  const isOpen = open;

  const meta = [
    source.article ? `Art. ${source.article}` : null,
    source.page != null ? `p.${source.page}` : null,
  ].filter((m): m is string => m !== null);

  return (
    <div
      id={elementId}
      className={`scroll-mt-24 overflow-hidden rounded-xl border bg-(--color-surface) shadow-soft transition-all duration-300 ${
        highlighted
          ? "border-accent-400 ring-4 ring-accent-500/15"
          : source.cited
            ? "border-(--color-border)"
            : "border-(--color-border) bg-(--color-surface)/60"
      }`}
    >
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center gap-3 px-3.5 py-3 text-start transition-colors hover:bg-(--color-surface-muted)/60 focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-accent-500"
        aria-expanded={isOpen}
      >
        <span
          aria-hidden="true"
          className={`flex h-6 w-6 shrink-0 items-center justify-center rounded-md text-[0.7rem] font-semibold tabular-nums ${
            source.cited
              ? "bg-accent-50 text-accent-700 ring-1 ring-inset ring-accent-200 dark:bg-accent-800/40 dark:text-accent-200 dark:ring-accent-700/60"
              : "bg-(--color-surface-muted) text-(--color-text-muted)"
          }`}
        >
          {source.number}
        </span>

        <div className="min-w-0 flex-1">
          <p
            className="truncate text-sm font-medium text-(--color-text)"
            dir={sourceDir}
            lang={source.language}
          >
            {source.law_title ?? source.document}
          </p>
          {meta.length > 0 && (
            <div className="mt-1 flex flex-wrap gap-1">
              {meta.map((m) => (
                <span
                  key={m}
                  className="rounded-md bg-(--color-surface-muted) px-1.5 py-px text-[0.68rem] font-medium text-(--color-text-muted)"
                >
                  {m}
                </span>
              ))}
            </div>
          )}
        </div>

        <ChevronDown
          size={16}
          aria-hidden="true"
          className={`shrink-0 text-(--color-text-muted) transition-transform duration-200 ${isOpen ? "rotate-180" : ""}`}
        />
      </button>

      <motion.div
        initial={false}
        animate={{ height: isOpen ? "auto" : 0, opacity: isOpen ? 1 : 0 }}
        transition={{ duration: 0.22, ease: "easeOut" }}
        className="overflow-hidden"
      >
        <div className="border-t border-(--color-border) px-3.5 pb-3.5 pt-3">
          <blockquote
            className="bidi-plaintext border-s-2 border-accent-300 ps-3 text-[0.82rem] leading-relaxed text-(--color-text-muted) dark:border-accent-700"
            dir={sourceDir}
            lang={source.language}
          >
            {displayedExcerpt}
          </blockquote>
          {isExcerptLong && (
            <button
              type="button"
              onClick={() => setFullExcerptShown((v) => !v)}
              className="mt-2 rounded text-xs font-medium text-accent-700 hover:underline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent-500 dark:text-accent-300"
            >
              {fullExcerptShown ? t("sources.hide") : t("sources.showFull")}
            </button>
          )}

          <div className="mt-3 flex items-center gap-2.5">
            <span className="text-[0.68rem] text-(--color-text-muted)">{t("sources.score")}</span>
            <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-(--color-surface-muted)" aria-hidden="true">
              <div
                className="h-full rounded-full bg-linear-to-r from-accent-400 to-accent-600"
                style={{ width: `${scorePct}%` }}
              />
            </div>
            <span className="w-8 text-end text-[0.68rem] font-medium tabular-nums text-(--color-text-muted)">
              {scorePct}%
            </span>
          </div>
        </div>
      </motion.div>
    </div>
  );
}
