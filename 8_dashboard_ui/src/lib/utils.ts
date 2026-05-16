import { type ClassValue, clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';
import type { EdgeKind, EntityKind, RiskTier } from '@/types/intel';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function tierColor(tier: RiskTier): string {
  switch (tier) {
    case 'critical':
      return 'var(--color-rose-500)';
    case 'high':
      return 'var(--color-amber-500)';
    case 'medium':
      return 'var(--color-ice-500)';
    case 'low':
      return 'var(--color-emerald-500)';
  }
}

export function tierLabel(tier: RiskTier): string {
  return tier.toUpperCase();
}

export function riskToTier(risk: number): RiskTier {
  if (risk >= 80) return 'critical';
  if (risk >= 60) return 'high';
  if (risk >= 35) return 'medium';
  return 'low';
}

export function entityGlyph(kind: EntityKind): string {
  switch (kind) {
    case 'person':
      return '◉';
    case 'shell_company':
      return '◍';
    case 'company':
      return '▣';
    case 'account':
      return '◇';
    case 'wallet':
      return '◆';
    case 'device':
      return '▤';
    case 'address':
      return '⌂';
    case 'transaction':
      return '↯';
    case 'phone':
      return '☏';
    case 'document':
      return '▦';
  }
}

export function edgeLabel(kind: EdgeKind): string {
  switch (kind) {
    case 'owns':
      return 'OWNS';
    case 'controls':
      return 'CONTROLS';
    case 'transfers':
      return 'TRANSFERS';
    case 'shares_device':
      return 'SHARES_DEVICE';
    case 'shares_address':
      return 'SHARES_ADDRESS';
    case 'shares_phone':
      return 'SHARES_PHONE';
    case 'employs':
      return 'EMPLOYS';
    case 'authorizes':
      return 'AUTHORIZES';
    case 'wires_to':
      return 'WIRES_TO';
    case 'kyc_match':
      return 'KYC_MATCH';
    case 'hidden_link':
      return 'HIDDEN_LINK';
  }
}

export function formatTime(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleTimeString('en-GB', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });
}

export function compactHash(id: string, len = 8): string {
  if (id.length <= len) return id;
  return id.slice(0, len);
}

export function toneClass(
  tone: 'ice' | 'amber' | 'rose' | 'violet' | 'emerald'
): { text: string; border: string; bg: string; glow: string } {
  switch (tone) {
    case 'ice':
      return {
        text: 'text-[var(--color-ice-400)]',
        border: 'border-[rgba(34,211,238,0.35)]',
        bg: 'bg-[rgba(34,211,238,0.06)]',
        glow: 'glow-ice',
      };
    case 'amber':
      return {
        text: 'text-[var(--color-amber-400)]',
        border: 'border-[rgba(245,158,11,0.35)]',
        bg: 'bg-[rgba(245,158,11,0.06)]',
        glow: 'glow-amber',
      };
    case 'rose':
      return {
        text: 'text-[var(--color-rose-400)]',
        border: 'border-[rgba(244,63,94,0.35)]',
        bg: 'bg-[rgba(244,63,94,0.06)]',
        glow: 'glow-rose',
      };
    case 'violet':
      return {
        text: 'text-[var(--color-violet-400)]',
        border: 'border-[rgba(168,85,247,0.35)]',
        bg: 'bg-[rgba(168,85,247,0.06)]',
        glow: 'glow-violet',
      };
    case 'emerald':
      return {
        text: 'text-[var(--color-emerald-400)]',
        border: 'border-[rgba(16,185,129,0.35)]',
        bg: 'bg-[rgba(16,185,129,0.06)]',
        glow: '',
      };
  }
}

export function clamp(n: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, n));
}
