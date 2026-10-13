interface CitationChipProps {
  number: number;
  onClick: () => void;
}

export function CitationChip({ number, onClick }: CitationChipProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="mx-0.5 inline-flex h-[1.2rem] min-w-[1.2rem] -translate-y-[0.15em] items-center justify-center rounded-full bg-accent-50 px-1.5 align-middle text-[0.68rem] font-semibold leading-none tabular-nums text-accent-700 ring-1 ring-inset ring-accent-200 transition-colors duration-150 hover:bg-accent-600 hover:text-white hover:ring-accent-600 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent-500 dark:bg-accent-800/50 dark:text-accent-200 dark:ring-accent-700 dark:hover:bg-accent-300 dark:hover:text-accent-800 dark:hover:ring-accent-300"
      aria-label={`Source ${number}`}
    >
      {number}
    </button>
  );
}
