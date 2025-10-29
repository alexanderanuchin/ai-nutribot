import { useEffect, useLayoutEffect } from 'react'
import legacyStyles from '../styles/base.css?inline'

let legacyRefCount = 0
let legacyStyleElement: HTMLStyleElement | null = null

const useIsomorphicLayoutEffect = typeof window !== 'undefined' ? useLayoutEffect : useEffect

export function useLegacyStyles(enabled = true): void {
  useIsomorphicLayoutEffect(() => {
    if (!enabled || typeof document === 'undefined') {
      return undefined
    }

    if (!legacyStyleElement) {
      legacyStyleElement = document.createElement('style')
      legacyStyleElement.setAttribute('data-legacy-styles', 'base')
      legacyStyleElement.textContent = legacyStyles
    }

    if (!legacyStyleElement.isConnected) {
      document.head.appendChild(legacyStyleElement)
    }

    legacyRefCount += 1
    document.body.classList.add('legacy-styles')

    return () => {
      if (typeof document === 'undefined') {
        return
      }

      legacyRefCount = Math.max(legacyRefCount - 1, 0)

      if (legacyRefCount === 0) {
        document.body.classList.remove('legacy-styles')

        if (legacyStyleElement) {
          legacyStyleElement.remove()
          legacyStyleElement = null
        }
      }
    }
    // ensure cleanup when enabled toggles to false
    // React calls this cleanup before the effect re-runs with enabled=false
  }, [enabled])
}
