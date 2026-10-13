import { motion, useReducedMotion } from "framer-motion";
import { ArrowUpRight, MessageCircleQuestion } from "lucide-react";
import { BrandMark } from "./BrandMark";
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
  const reduceMotion = useReducedMotion();

  return (
    <div className="mx-auto flex w-full max-w-[760px] flex-1 flex-col items-center justify-center gap-10 px-4 py-10 sm:py-16">
      <motion.div
        initial={reduceMotion ? false : { opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, ease: "easeOut" }}
        className="flex flex-col items-center text-center"
      >
        <BrandMark size="lg" />
        <h1 className="text-gradient mt-5 text-2xl font-semibold tracking-tight sm:text-3xl">{t("empty.title")}</h1>
        <p className="mt-2 max-w-md text-sm leading-relaxed text-(--color-text-muted)">{t("empty.subtitle")}</p>
      </motion.div>

      <div className="grid w-full gap-6 sm:grid-cols-2 sm:gap-4">
        <ExampleGroup label={t("empty.examplesFr")} examples={FR_EXAMPLES} lang="fr" onPick={onPick} delay={0.1} />
        <ExampleGroup label={t("empty.examplesAr")} examples={AR_EXAMPLES} lang="ar" onPick={onPick} delay={0.18} />
      </div>
    </div>
  );
}

function ExampleGroup({
  label,
  examples,
  lang,
  onPick,
  delay,
}: {
  label: string;
  examples: string[];
  lang: "fr" | "ar";
  onPick: (q: string) => void;
  delay: number;
}) {
  const reduceMotion = useReducedMotion();
  const dir = lang === "ar" ? "rtl" : "ltr";

  return (
    <motion.section
      initial={reduceMotion ? false : { opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, ease: "easeOut", delay }}
      aria-label={label}
    >
      <p className="mb-2.5 px-1 text-[0.7rem] font-semibold uppercase tracking-wider text-(--color-text-muted)">
        {label}
      </p>
      <ul className="flex flex-col gap-2">
        {examples.map((question) => (
          <li key={question}>
            <button
              type="button"
              dir={dir}
              lang={lang}
              onClick={() => onPick(question)}
              className="group flex w-full items-start gap-3 rounded-xl border border-(--color-border) bg-(--color-surface) px-3.5 py-3 text-start text-sm leading-snug text-(--color-text) shadow-soft transition-all duration-200 hover:-translate-y-0.5 hover:border-accent-300 hover:shadow-lift focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent-500 dark:hover:border-accent-700"
            >
              <span
                aria-hidden="true"
                className="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-accent-50 text-accent-700 ring-1 ring-inset ring-accent-100 transition-colors group-hover:bg-accent-100 dark:bg-accent-800/40 dark:text-accent-300 dark:ring-accent-800"
              >
                <MessageCircleQuestion size={15} />
              </span>
              <span className="flex-1 pt-0.5">{question}</span>
              <ArrowUpRight
                size={16}
                aria-hidden="true"
                className="mt-1 shrink-0 text-(--color-text-muted) opacity-0 transition-all group-hover:text-accent-600 group-hover:opacity-100 group-focus-visible:opacity-100 rtl:-scale-x-100 dark:group-hover:text-accent-300"
              />
            </button>
          </li>
        ))}
      </ul>
    </motion.section>
  );
}
