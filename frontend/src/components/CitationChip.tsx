interface CitationChipProps {
  number: number;
  onClick: () => void;
}

export function CitationChip({ number, onClick }: CitationChipProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="mx-0.5 inline-flex h-[1.15rem] min-w-[1.15rem] -translate-y-px items-center justify-center rounded-md border border-accent-200 bg-accent-50 px-1 align-middle text-[0.68rem] font-semibold tabular-nums text-accent-700 transition-all hover:-translate-y-0.5 hover:border-accent-400 hover:bg-accent-100 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent-500 dark:border-accent-700/60 dark:bg-accent-800/40 dark:text-accent-200 dark:hover:bg-accent-700/50"
      aria-label={`Source ${number}`}
    >
      {number}
    </button>
  );
}
