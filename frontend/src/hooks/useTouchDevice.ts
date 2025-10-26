import { useEffect, useState } from 'react'

const TOUCH_MEDIA_QUERY = '(hover: none) and (pointer: coarse)'

type TouchNavigator = Navigator & { msMaxTouchPoints?: number }

function getNavigator(): TouchNavigator | undefined {
  if (typeof window !== 'undefined' && window.navigator) {
    return window.navigator as TouchNavigator
  }
  if (typeof navigator !== 'undefined') {
    return navigator as TouchNavigator
  }
  return undefined
}

function detectTouchSupport(): boolean {
  const nav = getNavigator()
  if (nav) {
    if (typeof nav.maxTouchPoints === 'number' && nav.maxTouchPoints > 0) {
      return true
    }
    if (typeof nav.msMaxTouchPoints === 'number' && nav.msMaxTouchPoints > 0) {
      return true
    }
  }
  if (typeof window !== 'undefined' && typeof window.matchMedia === 'function') {
    try {
      return window.matchMedia(TOUCH_MEDIA_QUERY).matches
    } catch (_error) {
      return false
    }
  }
  return false
}

export function useTouchDevice(): boolean {
  const [isTouchDevice, setIsTouchDevice] = useState<boolean>(() => detectTouchSupport())

  useEffect(() => {
    if (typeof window === 'undefined') return undefined

    const update = () => {
      setIsTouchDevice(detectTouchSupport())
    }

    update()

    const media = typeof window.matchMedia === 'function' ? window.matchMedia(TOUCH_MEDIA_QUERY) : null

    const handleMediaChange = () => update()

    if (media) {
      if (typeof media.addEventListener === 'function') {
        media.addEventListener('change', handleMediaChange)
      } else if (typeof media.addListener === 'function') {
        media.addListener(handleMediaChange)
      }
    }

    window.addEventListener('orientationchange', update)
    window.addEventListener('resize', update)
    window.addEventListener('touchstart', update, { passive: true })
    window.addEventListener('pointerdown', update, { passive: true })

    return () => {
      if (media) {
        if (typeof media.removeEventListener === 'function') {
          media.removeEventListener('change', handleMediaChange)
        } else if (typeof media.removeListener === 'function') {
          media.removeListener(handleMediaChange)
        }
      }

      window.removeEventListener('orientationchange', update)
      window.removeEventListener('resize', update)
      window.removeEventListener('touchstart', update)
      window.removeEventListener('pointerdown', update)
    }
  }, [])

  return isTouchDevice
}
