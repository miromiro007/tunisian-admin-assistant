import { useId, useState } from "react";
import { Info } from "lucide-react";

interface InfoTooltipProps {
  /** Accessible name of the trigger button. */
  label: string;
  text: string;
}

/** Shows on hover, keyboard focus and tap (touch has no hover); Escape dismisses it. */
export function InfoTooltip({ label, text }: InfoTooltipProps) {
  const id = useId();
  const [open, setOpen] = useState(false);

  return (
    <span className="relative inline-flex" onMouseEnter={() => setOpen(true)} onMouseLeave={() => setOpen(false)}>
      <button
        type="button"
        aria-label={label}
        aria-describedby={id}
        onClick={() => setOpen((v) => !v)}
        onFocus={() => setOpen(true)}
        onBlur={() => setOpen(false)}
        onKeyDown={(e) => {
          if (e.key === "Escape") setOpen(false);
        }}
        className="flex h-4 w-4 items-center justify-center rounded-full text-(--color-text-muted) transition-colors hover:text-(--color-text) focus-visible:outline-2 focus-visible:outline-offset-1 focus-visible:outline-accent-500"
      >
        <Info size={12} aria-hidden="true" />
      </button>
      <span
        role="tooltip"
        id={id}
        className={`pointer-events-none absolute bottom-full start-0 z-30 mb-1.5 w-60 max-w-[70vw] rounded-lg bg-(--color-text) px-2.5 py-1.5 text-[0.72rem] font-normal leading-snug text-(--color-bg) shadow-lift transition-opacity duration-150 ${
          open ? "opacity-100" : "opacity-0"
        }`}
      >
        {text}
      </span>
    </span>
  );
}
