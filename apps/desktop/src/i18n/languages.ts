import type { Locale } from './types'

export const DEFAULT_LOCALE: Locale = 'en'

export const LOCALE_OPTIONS = [
  {
    id: 'en',
    name: 'English',
    configValue: 'en'
  }
] as const satisfies readonly { configValue: string; id: Locale; name: string }[]

// Travis's build is English-only. Keep unsupported saved locale values from
// activating non-English UI while leaving upstream locale files untouched.
export const LOCALE_META: Record<Locale, { name: string }> = Object.fromEntries(
  LOCALE_OPTIONS.map(locale => [locale.id, { name: locale.name }])
) as Record<Locale, { name: string }>

const LOCALE_ALIASES: Record<string, Locale> = {
  en: 'en',
  'en-us': 'en',
  en_us: 'en'
}

export function isLocale(value: unknown): value is Locale {
  return typeof value === 'string' && LOCALE_OPTIONS.some(locale => locale.id === value)
}

export function normalizeLocale(value: unknown): Locale {
  if (typeof value !== 'string') {
    return DEFAULT_LOCALE
  }

  return LOCALE_ALIASES[value.trim().toLowerCase()] ?? DEFAULT_LOCALE
}

export function isSupportedLocaleValue(value: unknown): boolean {
  return typeof value === 'string' && LOCALE_ALIASES[value.trim().toLowerCase()] != null
}

export function localeConfigValue(locale: Locale): string {
  return LOCALE_OPTIONS.find(item => item.id === locale)?.configValue ?? DEFAULT_LOCALE
}
