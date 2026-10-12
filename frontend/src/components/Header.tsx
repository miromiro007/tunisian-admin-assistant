import { MessageSquarePlus } from "lucide-react";
import { ThemeToggle } from "./ThemeToggle";
import { LangSwitch } from "./LangSwitch";
import { useLang } from "../i18n";

interface HeaderProps {
  onNewConversation: () => void;
  canStartNew: boolean;
}

export function Header({ onNewConversation, canStartNew }: HeaderProps) {
  const { t } = useLang();

  return (
    <header className="sticky top-0 z-10 border-b border-(--color-border) bg-(--color-bg)/80 backdrop-blur-md">
      <div className="mx-auto flex max-w-[760px] items-center justify-between px-4 py-3">
        <p className="truncate text-sm font-semibold text-(--color-text)">{t("app.name")}</p>
        <div className="flex items-center gap-2">
          {canStartNew && (
            <button
              type="button"
              onClick={onNewConversation}
              className="flex items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-xs font-medium text-(--color-text-muted) transition-colors hover:bg-(--color-surface-muted) hover:text-(--color-text) focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent-500"
            >
              <MessageSquarePlus size={14} />
              {t("app.newConversation")}
            </button>
          )}
          <LangSwitch />
          <ThemeToggle />
        </div>
      </div>
    </header>
  );
}
