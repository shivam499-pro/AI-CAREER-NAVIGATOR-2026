/**
 * Brand Tokens - Phase 3 (OCP Fix)
 * Data-driven config map replaces hardcoded if/else in getBrandColor.
 * Adding a new company = add one entry here. No function changes needed.
 */

export const BRAND_COLORS: Record<string, string> = {
  microsoft: '#0078D4',
  google: '#34A853',
  amazon: '#FF9900',
  aws: '#FF9900',
  flipkart: '#F77F00',
  freshworks: '#FF6B6B',
  swiggy: '#FC8019',
  ola: '#3BAB6F',
  zomato: '#E23744',
  meta: '#1877F2',
  facebook: '#1877F2',
  apple: '#A2AAAD',
  netflix: '#E50914',
}

export const DEFAULT_BRAND_COLOR = '#6C3FC8'

export function getBrandColor(name: string): string {
  const lower = name.toLowerCase()
  const match = Object.keys(BRAND_COLORS).find(key => lower.includes(key))
  return match ? BRAND_COLORS[match] : DEFAULT_BRAND_COLOR
}

export const EXPERIENCE_STYLES: Record<string, string> = {
  beginner: 'bg-sky-500/10 text-sky-400 border-sky-500/25',
  senior: 'bg-amber-500/10 text-amber-400 border-amber-500/25',
  default: 'bg-primary-violet/10 text-primary-violet border-primary-violet/25',
}

export function getExperienceStyles(level: string): string {
  const lower = level.toLowerCase()
  if (lower.includes('beginner')) return EXPERIENCE_STYLES.beginner
  if (lower.includes('senior')) return EXPERIENCE_STYLES.senior
  return EXPERIENCE_STYLES.default
}