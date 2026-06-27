import { type ClassValue, clsx } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}
// ADD to lib/utils.ts
export function formatUsername(email: string): string {
  const prefix = email.split('@')[0]
  const match = prefix.match(/^[a-zA-Z]+/)
  if (match) return match[0].charAt(0).toUpperCase() + match[0].slice(1).toLowerCase()
  return prefix.charAt(0).toUpperCase() + prefix.slice(1)
}