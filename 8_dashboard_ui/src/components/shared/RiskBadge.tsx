import { cn, riskToTier, tierLabel } from '@/lib/utils';
import type { RiskTier } from '@/types/intel';

interface RiskBadgeProps {
  score?: number;
  tier?: RiskTier;
  size?: 'xs' | 'sm' | 'md';
  showScore?: boolean;
  className?: string;
}

const tierClass: Record<RiskTier, string> = {
  critical:
    'bg-[rgba(244,63,94,0.10)] text-[var(--color-rose-400)] border-[rgba(244,63,94,0.35)]',
  high: 'bg-[rgba(245,158,11,0.10)] text-[var(--color-amber-400)] border-[rgba(245,158,11,0.35)]',
  medium: 'bg-[rgba(34,211,238,0.10)] text-[var(--color-ice-400)] border-[rgba(34,211,238,0.35)]',
  low: 'bg-[rgba(16,185,129,0.10)] text-[var(--color-emerald-400)] border-[rgba(16,185,129,0.35)]',
};

export function RiskBadge({
  score,
  tier,
  size = 'sm',
  showScore = true,
  className,
}: RiskBadgeProps) {
  const t: RiskTier = tier ?? riskToTier(score ?? 0);
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 border rounded-sm font-mono uppercase tracking-wider',
        size === 'xs' && 'text-[9px] px-1.5 py-[1px]',
        size === 'sm' && 'text-[10px] px-2 py-[2px]',
        size === 'md' && 'text-[11px] px-2.5 py-1',
        tierClass[t],
        className
      )}
    >
      <span className="inline-block size-1 rounded-full bg-current" />
      <span>{tierLabel(t)}</span>
      {showScore && score !== undefined && (
        <span className="opacity-60">· {score}</span>
      )}
    </span>
  );
}
