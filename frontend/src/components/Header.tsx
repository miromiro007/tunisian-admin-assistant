import { Plus } from "lucide-react";
import { ThemeToggle } from "./ThemeToggle";
import { LangSwitch } from "./LangSwitch";
import { ProviderSwitch } from "./ProviderSwitch";
import { BrandMark } from "./BrandMark";
import { useLang } from "../i18n";
import type { Provider } from "../types";

interface HeaderProps {
  onNewConversation: () => void;
  canStartNew: boolean;
  provider: Provider;
  onProviderChange: (provider: Provider) => void;
}

export function Header({ onNewConversation, canStartNew, provider, onProviderChange }: HeaderProps) {
  const { t } = useLang();

  return (
    <header className="sticky top-0 z-20 border-b border-(--color-border)/70 bg-(--color-bg)/70 backdrop-blur-xl backdrop-saturate-150">
      <div className="mx-auto flex h-14 max-w-5xl items-center justify-between gap-2 px-3 sm:gap-3 sm:px-4">
        <div className="flex min-w-0 items-center gap-2.5">
          <BrandMark size="sm" />
          <div className="hidden min-w-0 leading-tight sm:block">
            <p className="truncate text-sm font-semibold tracking-tight text-(--color-text)">{t("app.name")}</p>
            <p className="hidden truncate text-[0.7rem] text-(--color-text-muted) lg:block">{t("app.tagline")}</p>
          </div>
        </div>

        <div className="flex shrink-0 items-center gap-1.5">
          {canStartNew && (
            <button
              type="button"
              onClick={onNewConversation}
              aria-label={t("app.newConversation")}
              title={t("app.newConversation")}
              className="flex h-9 min-w-9 items-center justify-center gap-1.5 rounded-lg border border-(--color-border) bg-(--color-surface) px-2 text-xs font-medium text-(--color-text) shadow-soft transition-colors hover:border-(--color-border-strong) hover:bg-(--color-surface-muted) focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent-500"
            >
              <Plus size={15} aria-hidden="true" />
              <span className="hidden lg:inline">{t("app.newConversation")}</span>
            </button>
          )}
          <ProviderSwitch provider={provider} onChange={onProviderChange} />
          <span aria-hidden="true" className="mx-0.5 hidden h-5 w-px bg-(--color-border) sm:block" />
          <LangSwitch />
          <ThemeToggle />
        </div>
      </div>
    </header>
  );
}
