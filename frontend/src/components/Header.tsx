import { Plus } from "lucide-react";
import { ThemeToggle } from "./ThemeToggle";
import { LangSwitch } from "./LangSwitch";
import { BrandMark } from "./BrandMark";
import { useLang } from "../i18n";

interface HeaderProps {
  onNewConversation: () => void;
  canStartNew: boolean;
}

export function Header({ onNewConversation, canStartNew }: HeaderProps) {
  const { t } = useLang();

  return (
    <header className="sticky top-0 z-20 border-b border-(--color-border)/70 bg-(--color-bg)/70 backdrop-blur-xl backdrop-saturate-150">
      <div className="mx-auto flex h-14 max-w-[760px] items-center justify-between gap-3 px-4">
        <div className="flex min-w-0 items-center gap-2.5">
          <BrandMark size="sm" />
          <div className="min-w-0 leading-tight">
            <p className="truncate text-sm font-semibold tracking-tight text-(--color-text)">{t("app.name")}</p>
            <p className="hidden truncate text-[0.7rem] text-(--color-text-muted) sm:block">{t("app.tagline")}</p>
          </div>
        </div>

        <div className="flex shrink-0 items-center gap-1.5">
          {canStartNew && (
            <button
              type="button"
              onClick={onNewConversation}
              aria-label={t("app.newConversation")}
              className="flex h-9 items-center gap-1.5 rounded-lg border border-(--color-border) bg-(--color-surface) px-2.5 text-xs font-medium text-(--color-text) shadow-soft transition-all hover:border-(--color-border-strong) hover:bg-(--color-surface-muted) focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent-500"
            >
              <Plus size={14} aria-hidden="true" />
              <span className="hidden sm:inline">{t("app.newConversation")}</span>
            </button>
          )}
          <LangSwitch />
          <ThemeToggle />
        </div>
      </div>
    </header>
  );
}
