import { useLang } from "../i18n";

const FR_EXAMPLES = [
  "Avant quelle date l'employeur doit-il verser les cotisations dues pour le trimestre écoulé ?",
  "À quel âge les mineurs peuvent-ils prendre leur retraite ?",
  "Quel est le délai de versement des allocations familiales ?",
];

const AR_EXAMPLES = [
  "كم تبلغ مدة الراحة السنوية للعملة الذين يقل سنهم عن ثمانية عشر عاما؟",
  "ما هي النسبة المئوية للزيادة في أجر الساعات الإضافية؟",
  "ما هي مدة التجربة القصوى للعمال الفلاحيين؟",
];

interface EmptyStateProps {
  onPick: (question: string) => void;
}

export function EmptyState({ onPick }: EmptyStateProps) {
  const { t } = useLang();

  return (
    <div className="flex flex-1 flex-col items-center justify-center gap-8 px-4 py-12 text-center">
      <div>
        <h1 className="text-xl font-semibold text-(--color-text)">{t("empty.title")}</h1>
        <p className="mt-1 text-sm text-(--color-text-muted)">{t("empty.subtitle")}</p>
      </div>

      <div className="grid w-full max-w-lg gap-4">
        <ExampleGroup label={t("empty.examplesFr")} examples={FR_EXAMPLES} dir="ltr" onPick={onPick} />
        <ExampleGroup label={t("empty.examplesAr")} examples={AR_EXAMPLES} dir="rtl" onPick={onPick} />
      </div>
    </div>
  );
}

function ExampleGroup({
  label,
  examples,
  dir,
  onPick,
}: {
  label: string;
  examples: string[];
  dir: "ltr" | "rtl";
  onPick: (q: string) => void;
}) {
  return (
    <div>
      <p className="mb-2 text-xs font-medium uppercase tracking-wide text-(--color-text-muted)">{label}</p>
      <div className="flex flex-col gap-2">
        {examples.map((question) => (
          <button
            key={question}
            type="button"
            dir={dir}
            lang={dir === "rtl" ? "ar" : "fr"}
            onClick={() => onPick(question)}
            className="rounded-xl border border-(--color-border) bg-(--color-surface) px-4 py-2.5 text-left text-sm text-(--color-text) transition-colors hover:border-accent-500 hover:bg-accent-50 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent-500 dark:hover:bg-accent-700/10"
            style={{ textAlign: dir === "rtl" ? "right" : "left" }}
          >
            {question}
          </button>
        ))}
      </div>
    </div>
  );
}
