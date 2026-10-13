import { SearchX } from "lucide-react";
import type { RefusalReason } from "../types";
import { useLang } from "../i18n";

interface RefusalCardProps {
  reason: RefusalReason;
}

export function RefusalCard({ reason }: RefusalCardProps) {
  const { t } = useLang();
  const reasonKey = reason ? `refusal.${reason}` : "refusal.no_sources";

  return (
    <div
      aria-live="polite"
      className="flex items-start gap-3.5 rounded-2xl border border-(--color-border) bg-linear-to-b from-(--color-surface) to-(--color-surface-muted) p-4 shadow-soft"
    >
      <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-(--color-surface-muted) text-(--color-text-muted) ring-1 ring-inset ring-(--color-border)">
        <SearchX size={17} aria-hidden="true" />
      </span>
      <div className="pt-0.5">
        <p className="text-sm font-semibold text-(--color-text)">{t("refusal.title")}</p>
        <p className="mt-1 text-sm leading-relaxed text-(--color-text-muted)">{t(reasonKey)}</p>
      </div>
    </div>
  );
}
