import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react'
import type { ReactNode } from 'react'

interface CommandPaletteContextValue {
  open: boolean
  openPalette: () => void
  closePalette: () => void
  togglePalette: () => void
  setOpen: (value: boolean) => void
}

const CommandPaletteContext = createContext<CommandPaletteContextValue | undefined>(undefined)

export function CommandPaletteProvider({ children }: { children: ReactNode }) {
  const [open, setOpen] = useState(false)

  const openPalette = useCallback(() => setOpen(true), [])
  const closePalette = useCallback(() => setOpen(false), [])
  const togglePalette = useCallback(() => setOpen(prev => !prev), [])

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      const isMac = navigator.platform.toLowerCase().includes('mac')
      const isModKey = isMac ? event.metaKey : event.ctrlKey
      if (isModKey && event.key.toLowerCase() === 'k') {
        event.preventDefault()
        openPalette()
      }
      if (event.key === 'Escape') {
        closePalette()
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [closePalette, openPalette])

  const value = useMemo(
    () => ({ open, openPalette, closePalette, togglePalette, setOpen }),
    [closePalette, open, openPalette, togglePalette],
  )

  return <CommandPaletteContext.Provider value={value}>{children}</CommandPaletteContext.Provider>
}

export function useCommandPalette() {
  const context = useContext(CommandPaletteContext)
  if (!context) {
    throw new Error('useCommandPalette must be used within CommandPaletteProvider')
  }
  return context
}