import '@testing-library/jest-dom/vitest'

if (!window.matchMedia) {
  window.matchMedia = function matchMedia(query: string) {
    return {
      matches: query.includes('(prefers-color-scheme: dark)')
        ? window.document.documentElement.dataset.theme === 'dark'
        : false,
      media: query,
      onchange: null,
      addListener: () => {},
      removeListener: () => {},
      addEventListener: () => {},
      removeEventListener: () => {},
      dispatchEvent: () => false,
    }
  }
}