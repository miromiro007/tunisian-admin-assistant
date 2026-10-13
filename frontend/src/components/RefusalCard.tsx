import { Cloud, SearchX } from "lucide-react";
import type { RefusalReason } from "../types";
import { useLang } from "../i18n";

interface RefusalCardProps {
  reason: RefusalReason;
  /** Provided only while the Local model is selected; offers switching to Cloud on model_declined. */
  onSwitchToCloud?: () => void;
}

export function RefusalCard({ reason, onSwitchToCloud }: RefusalCardProps) {
  const { t } = useLang();
  const reasonKey = reason ? `refusal.${reason}` : "refusal.no_sources";
  // Retrieval found nothing usable vs. the model itself failing to produce an answer.
  const titleKey = reason === "model_declined" || reason === "empty_answer" ? "refusal.titleModel" : "refusal.title";
  const offerCloud = reason === "model_declined" && onSwitchToCloud !== undefined;

  return (
    <div className="flex items-start gap-3.5 rounded-2xl border border-(--color-border) bg-(--color-surface) p-4 shadow-soft sm:p-5">
      <span className="relative flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-linear-to-br from-(--color-surface-muted) to-(--color-border) text-(--color-text-muted)">
        <span aria-hidden="true" className="absolute inset-0 rounded-xl ring-1 ring-inset ring-(--color-border-strong)/40" />
        <SearchX size={18} aria-hidden="true" />
      </span>
      <div className="min-w-0 pt-0.5">
        <p className="text-[0.95rem] font-semibold text-(--color-text)">{t(titleKey)}</p>
        <p className="mt-1 text-sm leading-relaxed text-(--color-text-muted)">{t(reasonKey)}</p>
        {offerCloud && (
          <div className="mt-3 flex flex-wrap items-center gap-x-3 gap-y-2">
            <p className="text-sm text-(--color-text-muted)">{t("refusal.switchHint")}</p>
            <button
              type="button"
              onClick={onSwitchToCloud}
              className="inline-flex items-center gap-1.5 rounded-lg border border-(--color-border) bg-(--color-surface) px-3 py-1.5 text-xs font-semibold text-(--color-text) shadow-soft transition-colors hover:border-accent-400 hover:text-accent-700 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent-500 dark:hover:text-accent-300"
            >
              <Cloud size={13} aria-hidden="true" />
              {t("refusal.switchToCloud")}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
