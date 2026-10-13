import { useLang, type UiLang } from "../i18n";

const OPTIONS: { value: UiLang; label: string }[] = [
  { value: "fr", label: "FR" },
  { value: "ar", label: "AR" },
  { value: "en", label: "EN" },
];

export function LangSwitch() {
  const { lang, setLang, t } = useLang();

  return (
    <fieldset
      aria-label={t("lang.switch")}
      className="m-0 flex h-9 items-center gap-0.5 rounded-lg border border-(--color-border) bg-(--color-surface-muted) p-0.5"
    >
      {OPTIONS.map((option) => (
        <button
          key={option.value}
          type="button"
          onClick={() => setLang(option.value)}
          aria-pressed={lang === option.value}
          className={`flex h-full min-w-8 items-center justify-center rounded-md px-1.5 text-xs font-semibold transition-all focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-accent-500 ${
            lang === option.value
              ? "bg-(--color-surface) text-(--color-text) shadow-soft"
              : "text-(--color-text-muted) hover:text-(--color-text)"
          }`}
        >
          {option.label}
        </button>
      ))}
    </fieldset>
  );
}
