import { useMemo, useState } from "react";
import { ChevronDown } from "lucide-react";
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
    setHighlighted(number);
    document.getElementById(sourceElementId(turnId, number))?.scrollIntoView({
      behavior: "smooth",
      block: "center",
    });
    setTimeout(() => setHighlighted((cur) => (cur === number ? null : cur)), 2000);
  };

  if (showWarmingUp && text.length === 0) {
    return (
      <div className="rounded-xl border border-(--color-border) bg-(--color-surface) p-4">
        <p className="text-sm text-(--color-text-muted)">{t("warming.message")}</p>
      </div>
    );
  }

  if (isStreaming && text.length === 0 && sources.length === 0) {
    return <Skeleton />;
  }

  return (
    <div className="flex flex-col gap-3">
      {finalResponse?.refused ? (
        <RefusalCard reason={finalResponse.refusal_reason} />
      ) : (
        <p
          className="bidi-plaintext text-[0.95rem] leading-relaxed text-(--color-text)"
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
        <div className="flex flex-col gap-2">
          {citedSources.length > 0 && (
            <>
              <p className="text-xs font-medium uppercase tracking-wide text-(--color-text-muted)">
                {t("sources.title")}
              </p>
              {citedSources.map((source) => (
                <SourceCard
                  key={source.number}
                  source={source}
                  elementId={sourceElementId(turnId, source.number)}
                  highlighted={highlighted === source.number}
                />
              ))}
            </>
          )}

          {otherSources.length > 0 && (
            <div>
              <button
                type="button"
                onClick={() => setShowOthers((v) => !v)}
                className="flex items-center gap-1 text-xs font-medium text-(--color-text-muted) hover:text-(--color-text)"
                aria-expanded={showOthers}
              >
                <ChevronDown size={14} className={`transition-transform ${showOthers ? "rotate-180" : ""}`} />
                {t("sources.other")} ({otherSources.length})
              </button>
              {showOthers && (
                <div className="mt-2 flex flex-col gap-2">
                  {otherSources.map((source) => (
                    <SourceCard
                      key={source.number}
                      source={source}
                      elementId={sourceElementId(turnId, source.number)}
                      highlighted={highlighted === source.number}
                    />
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {finalResponse && <TimingsFooter response={finalResponse} />}
    </div>
  );
}

function sourceElementId(turnId: string, number: number): string {
  return `source-${turnId}-${number}`;
}

function Caret() {
  return <span className="ml-0.5 inline-block h-4 w-0.5 animate-pulse bg-accent-500 align-middle" aria-hidden="true" />;
}

function Skeleton() {
  return (
    <div className="flex flex-col gap-2" aria-hidden="true">
      <div className="h-3.5 w-5/6 animate-pulse rounded bg-(--color-surface-muted)" />
      <div className="h-3.5 w-full animate-pulse rounded bg-(--color-surface-muted)" />
      <div className="h-3.5 w-2/3 animate-pulse rounded bg-(--color-surface-muted)" />
    </div>
  );
}

function TimingsFooter({ response }: { response: AskResponse }) {
  const { t } = useLang();
  const { timings } = response;
  if (timings.first_token_ms == null) {
    return (
      <p className="text-xs text-(--color-text-muted)">
        {(timings.total_ms / 1000).toFixed(1)}s
      </p>
    );
  }
  return (
    <p className="text-xs text-(--color-text-muted)">
      {t("timings.summary", {
        first: (timings.first_token_ms / 1000).toFixed(1),
        total: (timings.total_ms / 1000).toFixed(1),
      })}
    </p>
  );
}
