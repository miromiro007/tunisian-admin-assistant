import { AlertTriangle, RotateCw } from "lucide-react";
import { useLang } from "../i18n";
import type { ErrorKind } from "../hooks/useAsk";

interface ErrorBannerProps {
  kind: ErrorKind;
  onRetry: () => void;
}

export function ErrorBanner({ kind, onRetry }: ErrorBannerProps) {
  const { t } = useLang();
  const messageKey =
    kind === "validation" ? "error.validation" : kind === "network" ? "error.network" : "error.serviceUnavailable";

  return (
    <div
      role="alert"
      className="flex items-start gap-3.5 rounded-2xl border border-red-200 bg-red-50/80 p-4 shadow-soft dark:border-red-500/25 dark:bg-red-950/30"
    >
      <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-red-100 text-red-700 dark:bg-red-500/15 dark:text-red-300">
        <AlertTriangle size={17} aria-hidden="true" />
      </span>
      <div className="flex-1 pt-0.5">
        <p className="text-sm leading-relaxed text-red-900 dark:text-red-100">{t(messageKey)}</p>
        <button
          type="button"
          onClick={onRetry}
          className="mt-3 inline-flex items-center gap-1.5 rounded-lg bg-(--color-surface) px-3 py-1.5 text-xs font-semibold text-red-800 shadow-soft ring-1 ring-inset ring-red-200 transition-colors hover:bg-red-100 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-red-500 dark:text-red-200 dark:ring-red-500/30 dark:hover:bg-red-900/40"
        >
          <RotateCw size={13} aria-hidden="true" />
          {t("error.retry")}
        </button>
      </div>
    </div>
  );
}
