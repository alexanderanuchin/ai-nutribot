import { describe, expect, it } from 'vitest'
import { DEFAULT_BASE_PATH, inferBasePath, resolveBasePath, sanitizeBasePath } from './basePath'

// getAppBasePath relies on window/import.meta; tests cover the pure helpers.

describe('sanitizeBasePath', () => {
  it('returns root for falsy values', () => {
    expect(sanitizeBasePath()).toBe(DEFAULT_BASE_PATH)
    expect(sanitizeBasePath('   ')).toBe(DEFAULT_BASE_PATH)
  })

  it('normalizes plain paths', () => {
    expect(sanitizeBasePath('crm')).toBe('/crm')
    expect(sanitizeBasePath('/crm/app/')).toBe('/crm/app')
  })

  it('extracts path from full URLs', () => {
    expect(sanitizeBasePath('https://app.example.com/mini/')).toBe('/mini')
  })

  it('ignores everything after the first candidate', () => {
    expect(
      sanitizeBasePath('https://mini.example.com/app/, https://backup.example.com'),
    ).toBe('/app')
  })

  it('supports newline or semicolon separated lists', () => {
    expect(sanitizeBasePath('https://mini.example.com/; https://other')).toBe('/')
    expect(sanitizeBasePath('https://mini.example.com/app\nhttps://other')).toBe('/app')
  })
})

describe('inferBasePath', () => {
  it('treats known routes as root-hosted', () => {
    expect(inferBasePath('/feed')).toBe(DEFAULT_BASE_PATH)
    expect(inferBasePath('/login')).toBe(DEFAULT_BASE_PATH)
  })

  it('falls back to the first segment otherwise', () => {
    expect(inferBasePath('/crm/feed')).toBe('/crm')
    expect(inferBasePath('/crm/app/unknown')).toBe('/crm')
  })
})

describe('resolveBasePath', () => {
  it('prefers explicit env base path', () => {
    expect(resolveBasePath('/whatever', '/crm/app')).toBe('/crm/app')
  })

  it('falls back to baseUrl when env base is root', () => {
    expect(resolveBasePath('/whatever', '/', '/mini-app')).toBe('/mini-app')
  })

  it('uses inferred prefix when no hints provided', () => {
    expect(resolveBasePath('/crm/feed')).toBe('/crm')
  })
})
