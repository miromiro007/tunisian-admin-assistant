import { useEffect, useRef, useState } from "react";
import { ArrowUp, Square } from "lucide-react";
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
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  };

  return (
    <div className="sticky bottom-0 border-t border-(--color-border) bg-(--color-bg)/80 px-4 py-3 backdrop-blur-md">
      <div className="mx-auto flex max-w-[760px] items-end gap-2 rounded-2xl border border-(--color-border) bg-(--color-surface) p-2 shadow-sm">
        <textarea
          ref={textareaRef}
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={handleKeyDown}
          dir={dir}
          rows={1}
          placeholder={t("input.placeholder")}
          aria-label={t("input.placeholder")}
          className="max-h-[200px] flex-1 resize-none bg-transparent px-2 py-1.5 text-sm text-(--color-text) placeholder:text-(--color-text-muted) focus:outline-none"
        />
        <button
          type="button"
          onClick={isStreaming ? onStop : submit}
          disabled={!isStreaming && value.trim().length === 0}
          aria-label={isStreaming ? t("input.stop") : t("input.send")}
          className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-accent-500 text-white transition-colors hover:bg-accent-600 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent-500 disabled:cursor-not-allowed disabled:opacity-40"
        >
          {isStreaming ? <Square size={16} /> : <ArrowUp size={18} />}
        </button>
      </div>
      <p className="mx-auto mt-1.5 max-w-[760px] text-center text-[0.7rem] text-(--color-text-muted)">
        {t("input.hint")}
      </p>
    </div>
  );
}
