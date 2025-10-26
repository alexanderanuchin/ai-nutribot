import { useEffect } from 'react'

export interface BodyScrollLockOptions {
  lock?: boolean
}

export function useBodyScrollLock(active = true): void {
  useEffect(() => {
    if (!active) return undefined
    if (typeof document === 'undefined') return undefined

    const { body, documentElement } = document
    const previousBodyOverflow = body.style.overflow
    const previousBodyTouchAction = body.style.touchAction
    const previousBodyOverscroll = body.style.overscrollBehavior
    const previousHtmlOverscroll = documentElement.style.overscrollBehavior

    body.style.overflow = 'hidden'
    body.style.touchAction = 'none'
    body.style.overscrollBehavior = 'contain'
    documentElement.style.overscrollBehavior = 'contain'

    return () => {
      body.style.overflow = previousBodyOverflow
      body.style.touchAction = previousBodyTouchAction
      body.style.overscrollBehavior = previousBodyOverscroll
      documentElement.style.overscrollBehavior = previousHtmlOverscroll
    }
  }, [active])
}