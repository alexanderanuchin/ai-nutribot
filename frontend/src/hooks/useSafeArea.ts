import { useMemo } from 'react'
import type { CSSProperties } from 'react'

export interface SafeAreaOptions {
  inset?: number
  axis?: 'vertical' | 'horizontal' | 'all'
  edges?: Array<'top' | 'right' | 'bottom' | 'left'>
}

export function useSafeArea({ inset = 12, axis = 'all', edges }: SafeAreaOptions = {}) {
  const padding = `${inset}px`
  return useMemo(() => {
    const style: CSSProperties = {}
    const axisEdges: Array<'top' | 'right' | 'bottom' | 'left'> = edges
      ? edges
      : axis === 'vertical'
        ? ['top', 'bottom']
        : axis === 'horizontal'
          ? ['left', 'right']
          : ['top', 'right', 'bottom', 'left']

    if (axisEdges.includes('top')) {
      style.paddingTop = `calc(env(safe-area-inset-top, 0px) + ${padding})`
    }
    if (axisEdges.includes('bottom')) {
      style.paddingBottom = `calc(env(safe-area-inset-bottom, 0px) + ${padding})`
    }
    if (axisEdges.includes('left')) {
      style.paddingLeft = `calc(env(safe-area-inset-left, 0px) + ${padding})`
    }
    if (axisEdges.includes('right')) {
      style.paddingRight = `calc(env(safe-area-inset-right, 0px) + ${padding})`
    }

    return style
  }, [axis, edges, padding])
}