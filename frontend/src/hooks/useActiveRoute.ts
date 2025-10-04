import { useCallback, useMemo } from 'react'
import { matchPath, useLocation } from 'react-router-dom'
import type { NavItem, NavSection } from '../navigation/schema'

function pathMatches(current: string, target: string, exact: boolean) {
  const match = matchPath({ path: target, end: exact }, current)
  if (match) return true
  if (exact) return false
  if (target === '/') return current === '/' || current === ''
  return current.startsWith(target)
}

export function useActiveRoute() {
  const location = useLocation()

  const isActivePath = useCallback(
    (path?: string, exact = false) => {
      if (!path) return false
      return pathMatches(location.pathname, path, exact)
    },
    [location.pathname],
  )

  const isItemActive = useCallback(
    (item: NavItem): boolean => {
      if (item.path && isActivePath(item.path)) {
        return true
      }
      if (item.children && item.children.length > 0) {
        return item.children.some(isItemActive)
      }
      return false
    },
    [isActivePath],
  )

  const isSectionActive = useCallback(
    (section: NavSection) => section.items.some(isItemActive),
    [isItemActive],
  )

  const findActiveTrail = useCallback(
    (sections: NavSection[], primary: NavItem[] = []): NavItem[] => {
      for (const item of primary) {
        if (isItemActive(item)) {
          return [item]
        }
      }

      for (const section of sections) {
        for (const item of section.items) {
          if (isItemActive(item)) {
            if (item.children) {
              const childTrail = item.children.find(child => isItemActive(child))
              if (childTrail) {
                return [item, childTrail]
              }
            }
            return [item]
          }
        }
      }
      return []
    },
    [isItemActive],
  )

  return useMemo(
    () => ({
      pathname: location.pathname,
      isActivePath,
      isItemActive,
      isSectionActive,
      findActiveTrail,
    }),
    [findActiveTrail, isActivePath, isItemActive, isSectionActive, location.pathname],
  )
}