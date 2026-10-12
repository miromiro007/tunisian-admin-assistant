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
    <div className="flex items-start gap-3 rounded-xl border border-(--color-border) bg-(--color-surface-muted) p-4">
      <SearchX size={20} className="mt-0.5 shrink-0 text-(--color-text-muted)" aria-hidden="true" />
      <div>
        <p className="text-sm font-medium text-(--color-text)">{t("refusal.title")}</p>
        <p className="mt-1 text-sm text-(--color-text-muted)">{t(reasonKey)}</p>
      </div>
    </div>
  );
}
