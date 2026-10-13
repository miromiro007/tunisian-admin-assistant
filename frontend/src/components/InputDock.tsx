import { useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { ArrowUp, Info, ShieldCheck, Square } from "lucide-react";
import { useLang } from "../i18n";
import type { Provider } from "../types";

const ARABIC_RE = /[؀-ۿ]/;

interface InputDockProps {
  onSubmit: (question: string) => void;
  onStop: () => void;
  isStreaming: boolean;
  provider: Provider;
}

export function InputDock({ onSubmit, onStop, isStreaming, provider }: InputDockProps) {
  const { t } = useLang();
  const [value, setValue] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const dir = ARABIC_RE.test(value) ? "rtl" : "ltr";
  const canSend = value.trim().length > 0;

  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 200)}px`;
  }, [value]);

  const submit = () => {
    const question = value.trim();
    if (!question || isStreaming) return;
    onSubmit(question);
    setValue("");
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) {
      e.preventDefault();
      submit();
    }
  };

  return (
    <div className="sticky bottom-0 z-10 bg-linear-to-t from-(--color-bg) from-60% to-transparent px-3 pb-3 pt-6 sm:px-4 sm:pb-4">
      <div className="mx-auto max-w-[760px]">
        <div className="flex items-end gap-2 rounded-2xl border border-(--color-border) bg-(--color-surface)/90 p-2 shadow-lift backdrop-blur-xl transition-[border-color,box-shadow] duration-200 focus-within:border-accent-500 focus-within:ring-4 focus-within:ring-accent-500/20">
          <textarea
            ref={textareaRef}
            value={value}
            onChange={(e) => setValue(e.target.value)}
            onKeyDown={handleKeyDown}
            dir={dir}
            lang={dir === "rtl" ? "ar" : undefined}
            rows={1}
            placeholder={t("input.placeholder")}
            aria-label={t("input.placeholder")}
            className="block max-h-[200px] min-h-10 flex-1 resize-none bg-transparent px-2.5 py-2 text-base leading-6 text-(--color-text) placeholder:text-(--color-text-muted) focus:outline-none"
          />
          <button
            type="button"
            onClick={isStreaming ? onStop : submit}
            disabled={!isStreaming && !canSend}
            aria-label={isStreaming ? t("input.stop") : t("input.send")}
            title={isStreaming ? t("input.stop") : t("input.send")}
            className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-xl transition-all focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent-500 disabled:cursor-not-allowed ${
              isStreaming
                ? "bg-(--color-text) text-(--color-bg) shadow-soft hover:opacity-85"
                : canSend
                  ? "bg-linear-to-br from-accent-500 to-accent-700 text-white shadow-soft hover:brightness-110 active:scale-95"
                  : "bg-(--color-surface-muted) text-(--color-text-muted)"
            }`}
          >
            {isStreaming ? <Square size={13} fill="currentColor" /> : <ArrowUp size={18} strokeWidth={2.25} />}
          </button>
        </div>

        <div aria-live="polite">
          <AnimatePresence initial={false}>
            {provider === "groq" && (
              <motion.p
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: "auto", opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                transition={{ duration: 0.2, ease: "easeOut" }}
                className="overflow-hidden"
              >
                <span className="mt-2 flex items-start gap-1.5 rounded-lg border border-amber-200 bg-amber-50 px-2.5 py-1.5 text-[0.72rem] leading-snug text-amber-900 dark:border-amber-500/25 dark:bg-amber-950/40 dark:text-amber-100">
                  <Info size={13} aria-hidden="true" className="mt-px shrink-0" />
                  {t("provider.cloudNotice")}
                </span>
              </motion.p>
            )}
          </AnimatePresence>
        </div>

        <footer className="mt-2 flex flex-col items-center gap-0.5 text-center">
          <p className="hidden text-[0.7rem] text-(--color-text-muted) sm:block">{t("input.hint")}</p>
          <p className="flex items-start justify-center gap-1.5 text-[0.72rem] leading-snug text-(--color-text-muted)">
            <ShieldCheck size={12} aria-hidden="true" className="mt-0.5 hidden shrink-0 sm:block" />
            {t("footer.disclaimer")}
          </p>
        </footer>
      </div>
    </div>
  );
}
