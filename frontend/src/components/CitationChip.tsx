interface CitationChipProps {
  number: number;
  onClick: () => void;
}

export function CitationChip({ number, onClick }: CitationChipProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="mx-0.5 inline-flex h-5 min-w-5 items-center justify-center rounded-full bg-accent-100 px-1.5 text-xs font-medium text-accent-700 transition-colors hover:bg-accent-300 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent-500 dark:bg-accent-700/30 dark:text-accent-300 dark:hover:bg-accent-700/50"
      aria-label={`Source ${number}`}
    >
      {number}
    </button>
  );
}
