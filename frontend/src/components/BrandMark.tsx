import { Scale } from "lucide-react";

const SIZES = {
  sm: { box: "h-8 w-8 rounded-lg", icon: 16 },
  md: { box: "h-9 w-9 rounded-xl", icon: 18 },
  lg: { box: "h-14 w-14 rounded-2xl", icon: 26 },
} as const;

export function BrandMark({ size = "md" }: { size?: keyof typeof SIZES }) {
  const s = SIZES[size];
  return (
    <span
      aria-hidden="true"
      className={`relative flex shrink-0 items-center justify-center bg-linear-to-br from-accent-400 to-accent-700 text-white shadow-soft ring-1 ring-inset ring-white/20 ${s.box}`}
    >
      <Scale size={s.icon} strokeWidth={2} />
    </span>
  );
}
