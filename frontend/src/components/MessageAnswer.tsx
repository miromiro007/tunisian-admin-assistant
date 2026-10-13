import { useMemo, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { BookOpen, ChevronDown, Clock, Cpu, Loader2 } from "lucide-react";
import { buildValidCitationNumbers, parseCitationMarkers } from "../lib/citations";
import { CitationChip } from "./CitationChip";
import { SourceCard } from "./SourceCard";
import { RefusalCard } from "./RefusalCard";
import { useLang } from "../i18n";
import type { AskResponse, Source } from "../types";

const EMPTY_INVALID_CITATIONS: number[] = [];

interface MessageAnswerProps {
  turnId: string;
  sources: Source[];
  streamedText: string;
  finalResponse: AskResponse | null;
  isStreaming: boolean;
  showWarmingUp: boolean;
}

export function MessageAnswer({
  turnId,
  sources,
  streamedText,
  finalResponse,
  isStreaming,
  showWarmingUp,
}: MessageAnswerProps) {
  const { t } = useLang();
  const [showOthers, setShowOthers] = useState(false);
  const [highlighted, setHighlighted] = useState<number | null>(null);

  // The displayed text: once `done` arrives, it REPLACES the streamed text (source of truth).
  const text = finalResponse ? finalResponse.answer : streamedText;
  const invalidCitations = finalResponse?.invalid_citations ?? EMPTY_INVALID_CITATIONS;
  const validNumbers = useMemo(
    () => buildValidCitationNumbers(sources.map((s) => s.number), invalidCitations),
    [sources, invalidCitations],
  );
  const segments = useMemo(() => parseCitationMarkers(text, validNumbers), [text, validNumbers]);

  const citedSources = sources.filter((s) => s.cited);
  const otherSources = sources.filter((s) => !s.cited);

  const handleCitationClick = (number: number) => {
    if (otherSources.some((s) => s.number === number)) setShowOthers(true);
    setHighlighted(number);
    // Wait a frame so a just-expanded "other sources" list exists before scrolling.
    requestAnimationFrame(() => {
      document.getElementById(sourceElementId(turnId, number))?.scrollIntoView({
        behavior: "smooth",
        block: "center",
      });
    });
    setTimeout(() => setHighlighted((cur) => (cur === number ? null : cur)), 2200);
  };

  if (showWarmingUp && text.length === 0) {
    return (
      <div className="inline-flex items-center gap-2.5 rounded-full border border-(--color-border) bg-(--color-surface) px-3.5 py-2 text-sm text-(--color-text-muted) shadow-soft">
        <Loader2 size={15} className="animate-spin text-accent-500" aria-hidden="true" />
        <span aria-live="polite">{t("warming.message")}</span>
      </div>
    );
  }

  if (isStreaming && text.length === 0 && sources.length === 0) {
    return <Skeleton label={t("answer.searching")} />;
  }

  return (
    <div className="flex flex-col gap-5">
      {finalResponse?.refused ? (
        <RefusalCard reason={finalResponse.refusal_reason} />
      ) : (
        <p
          className="bidi-plaintext whitespace-pre-wrap pt-1 text-[0.95rem] leading-7 text-(--color-text)"
          dir="auto"
          aria-live="polite"
        >
          {segments.map((segment, i) =>
            segment.kind === "text" ? (
              <span key={i}>{segment.value}</span>
            ) : segment.valid ? (
              <CitationChip key={i} number={segment.number} onClick={() => handleCitationClick(segment.number)} />
            ) : (
              <span key={i}>[{segment.number}]</span>
            ),
          )}
          {isStreaming && !finalResponse && <Caret />}
        </p>
      )}

      {sources.length > 0 && (
        <section className="flex flex-col gap-2.5" aria-label={t("sources.title")}>
          {citedSources.length > 0 && (
            <>
              <h2 className="flex items-center gap-1.5 text-[0.7rem] font-semibold uppercase tracking-wider text-(--color-text-muted)">
                <BookOpen size={13} aria-hidden="true" />
                {t("sources.title")}
                <span className="rounded-full bg-(--color-surface-muted) px-1.5 py-px text-[0.65rem] tabular-nums">
                  {citedSources.length}
                </span>
              </h2>
              <div className="flex flex-col gap-2">
                {citedSources.map((source) => (
                  <SourceCard
                    key={source.number}
                    source={source}
                    elementId={sourceElementId(turnId, source.number)}
                    highlighted={highlighted === source.number}
                  />
                ))}
              </div>
            </>
          )}

          {otherSources.length > 0 && (
            <div>
              <button
                type="button"
                onClick={() => setShowOthers((v) => !v)}
                className="inline-flex items-center gap-1.5 rounded-full border border-(--color-border) px-3 py-1 text-xs font-medium text-(--color-text-muted) transition-colors hover:border-(--color-border-strong) hover:text-(--color-text) focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent-500"
                aria-expanded={showOthers}
              >
                <ChevronDown
                  size={13}
                  aria-hidden="true"
                  className={`transition-transform duration-200 ${showOthers ? "rotate-180" : ""}`}
                />
                {t("sources.other")}
                <span className="tabular-nums opacity-70">{otherSources.length}</span>
              </button>
              <AnimatePresence initial={false}>
                {showOthers && (
                  <motion.div
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: "auto", opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }}
                    transition={{ duration: 0.2, ease: "easeOut" }}
                    className="overflow-hidden"
                  >
                    <div className="flex flex-col gap-2 pt-2.5">
                      {otherSources.map((source) => (
                        <SourceCard
                          key={source.number}
                          source={source}
                          elementId={sourceElementId(turnId, source.number)}
                          highlighted={highlighted === source.number}
                        />
                      ))}
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          )}
        </section>
      )}

      {finalResponse && <MetaFooter response={finalResponse} />}
    </div>
  );
}

function sourceElementId(turnId: string, number: number): string {
  return `source-${turnId}-${number}`;
}

function Caret() {
  return (
    <span
      className="ms-0.5 inline-block h-[1.1em] w-[2px] translate-y-[0.2em] animate-blink rounded-full bg-accent-500"
      aria-hidden="true"
    />
  );
}

function Skeleton({ label }: { label: string }) {
  return (
    <div className="flex flex-col gap-3 pt-1.5">
      <p aria-live="polite" className="text-xs text-(--color-text-muted)">
        {label}
      </p>
      <div className="flex flex-col gap-2.5" aria-hidden="true">
        <div className="skeleton-line h-3 w-11/12 animate-shimmer rounded-full" />
        <div className="skeleton-line h-3 w-full animate-shimmer rounded-full" />
        <div className="skeleton-line h-3 w-3/5 animate-shimmer rounded-full" />
      </div>
    </div>
  );
}

function MetaFooter({ response }: { response: AskResponse }) {
  const { t } = useLang();
  const { timings } = response;
  const timingsLine =
    timings.first_token_ms == null
      ? `${(timings.total_ms / 1000).toFixed(1)}s`
      : t("timings.summary", {
          first: (timings.first_token_ms / 1000).toFixed(1),
          total: (timings.total_ms / 1000).toFixed(1),
        });

  return (
    <p className="flex flex-wrap items-center gap-x-3 gap-y-1 text-[0.7rem] text-(--color-text-muted)">
      <span className="inline-flex items-center gap-1">
        <Clock size={12} aria-hidden="true" />
        {timingsLine}
      </span>
      <span className="inline-flex items-center gap-1" dir="ltr">
        <Cpu size={12} aria-hidden="true" />
        {response.provider} / {response.model}
      </span>
    </p>
  );
}
