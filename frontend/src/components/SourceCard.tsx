import { useState, type CSSProperties } from "react";
import { ChevronDown } from "lucide-react";
import { motion } from "framer-motion";
import type { Source } from "../types";
import { useLang } from "../i18n";
import { lawHue } from "../lib/lawColor";
import { InfoTooltip } from "./InfoTooltip";

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
  const lawTitle = source.law_title ?? source.document;
  const isExcerptLong = source.excerpt.length > EXCERPT_COLLAPSE_LENGTH;
  const displayedExcerpt =
    isExcerptLong && !fullExcerptShown
      ? `${source.excerpt.slice(0, EXCERPT_COLLAPSE_LENGTH)}…`
      : source.excerpt;
  const similarity = Math.min(1, Math.max(0, source.score));

  const meta = [
    source.article ? `Art. ${source.article}` : null,
    source.page != null ? `p.${source.page}` : null,
  ].filter((m): m is string => m !== null);

  return (
    <div
      id={elementId}
      className={`scroll-mt-24 overflow-hidden rounded-xl border bg-(--color-surface) shadow-soft transition-[box-shadow,border-color] duration-300 ${
        highlighted ? "border-accent-400 ring-4 ring-accent-500/15" : "border-(--color-border)"
      } ${source.cited ? "border-s-[3px] border-s-accent-500" : ""}`}
    >
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-start gap-3 px-3.5 py-3 text-start transition-colors hover:bg-(--color-surface-muted)/60 focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-accent-500"
        aria-expanded={open}
      >
        <span
          aria-hidden="true"
          className={`mt-px flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-[0.7rem] font-semibold tabular-nums ${
            source.cited
              ? "bg-accent-600 text-white"
              : "bg-(--color-surface-muted) text-(--color-text-muted) ring-1 ring-inset ring-(--color-border)"
          }`}
        >
          {source.number}
        </span>

        <div className="flex min-w-0 flex-1 flex-col items-start gap-1">
          <span
            className="law-badge max-w-full truncate rounded-md px-2 py-0.5 text-[0.72rem] font-semibold"
            style={{ "--law-h": lawHue(lawTitle) } as CSSProperties}
            dir={sourceDir}
            lang={source.language}
            title={lawTitle}
          >
            {lawTitle}
          </span>
          {meta.length > 0 && (
            <span className="text-xs font-medium text-(--color-text-muted)" dir="ltr">
              {meta.join(" · ")}
            </span>
          )}
        </div>

        <ChevronDown
          size={16}
          aria-hidden="true"
          className={`mt-1 shrink-0 text-(--color-text-muted) transition-transform duration-200 ${open ? "rotate-180" : ""}`}
        />
      </button>

      <motion.div
        initial={false}
        animate={{ height: open ? "auto" : 0, opacity: open ? 1 : 0 }}
        transition={{ duration: 0.24, ease: [0.25, 0.1, 0.25, 1] }}
        className="overflow-hidden"
      >
        <div className="px-3.5 pb-3.5">
          <blockquote
            className="bidi-plaintext rounded-lg bg-(--color-surface-muted) px-3 py-2.5 text-[0.85rem] leading-relaxed text-(--color-text)"
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

          <div className="mt-3 flex items-center gap-2">
            <span className="inline-flex shrink-0 items-center gap-1 text-[0.7rem] text-(--color-text-muted)">
              {t("sources.score")}
              <InfoTooltip label={t("sources.scoreInfo")} text={t("sources.scoreHelp")} />
            </span>
            <div className="h-1 flex-1 overflow-hidden rounded-full bg-(--color-surface-muted)" aria-hidden="true">
              <div
                className="h-full rounded-full bg-(--color-text-muted)/50"
                style={{ width: `${similarity * 100}%` }}
              />
            </div>
            <span className="text-[0.7rem] font-medium tabular-nums text-(--color-text-muted)" dir="ltr">
              {similarity.toFixed(2)}
            </span>
          </div>
        </div>
      </motion.div>
    </div>
  );
}
