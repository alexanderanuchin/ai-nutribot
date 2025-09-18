import React from 'react'
import { useTheme } from '../hooks/useTheme'

export default function ThemeToggle(){
  const { theme, toggleTheme } = useTheme()
  const isLight = theme === 'light'

  return (
    <button
      type="button"
      className={`theme-toggle ${isLight ? 'is-light' : 'is-dark'}`}
      onClick={toggleTheme}
      role="switch"
      aria-checked={isLight}
      aria-label={`Переключить на ${isLight ? 'тёмную' : 'светлую'} тему`}
    >
      <span className="theme-toggle__track">
        <span className="theme-toggle__stars" aria-hidden="true" />
        <span className="theme-toggle__icon theme-toggle__icon--sun" aria-hidden="true">
          <svg viewBox="0 0 24 24" focusable="false" aria-hidden="true">
            <circle cx="12" cy="12" r="5" fill="currentColor" />
            <g stroke="currentColor" strokeWidth="1.5" strokeLinecap="round">
              <line x1="12" y1="2.5" x2="12" y2="5" />
              <line x1="12" y1="19" x2="12" y2="21.5" />
              <line x1="4.22" y1="4.22" x2="5.95" y2="5.95" />
              <line x1="18.05" y1="18.05" x2="19.78" y2="19.78" />
              <line x1="2.5" y1="12" x2="5" y2="12" />
              <line x1="19" y1="12" x2="21.5" y2="12" />
              <line x1="4.22" y1="19.78" x2="5.95" y2="18.05" />
              <line x1="18.05" y1="5.95" x2="19.78" y2="4.22" />
            </g>
          </svg>
        </span>
        <span className="theme-toggle__icon theme-toggle__icon--moon" aria-hidden="true">
          <svg viewBox="0 0 24 24" focusable="false" aria-hidden="true">
            <path
              fill="currentColor"
              d="M20.05 14.36a8.44 8.44 0 01-9.41-11.8 1 1 0 00-1.42-1.26A10.44 10.44 0 1019.45 15.8a1 1 0 00.6-1.44z"
            />
          </svg>
        </span>
        <span className="theme-toggle__cloud" aria-hidden="true" />
        <span className="theme-toggle__thumb" aria-hidden="true" />
      </span>
    </button>
  )
}