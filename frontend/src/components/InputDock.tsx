import { useEffect, useRef, useState } from "react";
import { ArrowUp, ShieldCheck, Square } from "lucide-react";
import { useLang } from "../i18n";

const ARABIC_RE = /[؀-ۿ]/;

interface InputDockProps {
  onSubmit: (question: string) => void;
  onStop: () => void;
  isStreaming: boolean;
}

export function InputDock({ onSubmit, onStop, isStreaming }: InputDockProps) {
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
        <div className="flex items-end gap-2 rounded-2xl border border-(--color-border) bg-(--color-surface)/90 p-2 shadow-lift backdrop-blur-xl transition-all focus-within:border-accent-400 focus-within:ring-4 focus-within:ring-accent-500/15 dark:focus-within:border-accent-600">
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
            className="max-h-[200px] min-h-10 flex-1 resize-none bg-transparent px-2.5 py-2 text-[0.95rem] leading-6 text-(--color-text) placeholder:text-(--color-text-muted)/80 focus:outline-none"
          />
          <button
            type="button"
            onClick={isStreaming ? onStop : submit}
            disabled={!isStreaming && !canSend}
            aria-label={isStreaming ? t("input.stop") : t("input.send")}
            className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-xl shadow-soft transition-all focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent-500 disabled:cursor-not-allowed disabled:shadow-none ${
              isStreaming
                ? "bg-(--color-text) text-(--color-bg) hover:opacity-85"
                : canSend
                  ? "bg-linear-to-br from-accent-500 to-accent-700 text-white hover:brightness-110 active:scale-95"
                  : "bg-(--color-surface-muted) text-(--color-text-muted)"
            }`}
          >
            {isStreaming ? <Square size={14} fill="currentColor" /> : <ArrowUp size={18} strokeWidth={2.25} />}
          </button>
        </div>

        <p className="mt-2 hidden text-center text-[0.7rem] text-(--color-text-muted) sm:block">{t("input.hint")}</p>
        <footer className="mt-1.5 flex items-start justify-center gap-1.5 text-center sm:mt-1">
          <ShieldCheck size={12} aria-hidden="true" className="mt-0.5 hidden shrink-0 text-(--color-text-muted) sm:block" />
          <p className="text-[0.7rem] leading-snug text-(--color-text-muted)">{t("footer.disclaimer")}</p>
        </footer>
      </div>
    </div>
  );
}
