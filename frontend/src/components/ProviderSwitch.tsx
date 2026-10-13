import { Cloud, Laptop } from "lucide-react";
import { useLang } from "../i18n";
import type { Provider } from "../types";

const OPTIONS: { value: Provider; labelKey: string; Icon: typeof Cloud }[] = [
  { value: "ollama", labelKey: "provider.local", Icon: Laptop },
  { value: "groq", labelKey: "provider.cloud", Icon: Cloud },
];

interface ProviderSwitchProps {
  provider: Provider;
  onChange: (provider: Provider) => void;
}

export function ProviderSwitch({ provider, onChange }: ProviderSwitchProps) {
  const { t } = useLang();

  return (
    <fieldset className="m-0 flex h-9 items-center gap-0.5 rounded-lg border border-(--color-border) bg-(--color-surface-muted) p-0.5">
      <legend className="sr-only">{t("provider.label")}</legend>
      {OPTIONS.map(({ value, labelKey, Icon }) => {
        const selected = provider === value;
        return (
          <button
            key={value}
            type="button"
            onClick={() => onChange(value)}
            aria-pressed={selected}
            title={t(labelKey)}
            className={`flex h-full min-w-8 items-center justify-center gap-1.5 rounded-md px-2 text-xs font-medium whitespace-nowrap transition-all focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-accent-500 ${
              selected
                ? "bg-(--color-surface) text-(--color-text) shadow-soft"
                : "text-(--color-text-muted) hover:text-(--color-text)"
            }`}
          >
            <Icon
              size={14}
              aria-hidden="true"
              className={selected ? "text-accent-600 dark:text-accent-300" : undefined}
            />
            <span className="sr-only md:not-sr-only">{t(labelKey)}</span>
          </button>
        );
      })}
    </fieldset>
  );
}
