import { Moon, Sun } from "lucide-react";
import { useTheme } from "../hooks/useTheme";
import { useLang } from "../i18n";

export function ThemeToggle() {
  const { theme, setTheme } = useTheme();
  const { t } = useLang();

  return (
    <button
      type="button"
      onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
      aria-label={t("theme.toggle")}
      className="flex h-9 w-9 items-center justify-center rounded-lg text-(--color-text-muted) transition-colors hover:bg-(--color-surface-muted) focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent-500"
    >
      {theme === "dark" ? <Sun size={18} /> : <Moon size={18} />}
    </button>
  );
}
