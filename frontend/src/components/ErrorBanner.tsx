import { AlertTriangle } from "lucide-react";
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
    <div className="flex items-start gap-3 rounded-xl border border-red-300/50 bg-red-50 p-4 dark:border-red-500/30 dark:bg-red-950/30">
      <AlertTriangle size={20} className="mt-0.5 shrink-0 text-red-600 dark:text-red-400" aria-hidden="true" />
      <div className="flex-1">
        <p className="text-sm text-red-800 dark:text-red-200">{t(messageKey)}</p>
        <button
          type="button"
          onClick={onRetry}
          className="mt-2 rounded-lg border border-red-300 px-3 py-1 text-xs font-medium text-red-700 transition-colors hover:bg-red-100 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-red-500 dark:border-red-500/40 dark:text-red-300 dark:hover:bg-red-900/40"
        >
          {t("error.retry")}
        </button>
      </div>
    </div>
  );
}
