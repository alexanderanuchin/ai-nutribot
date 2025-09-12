export function tg(){ return (window as any).Telegram?.WebApp }
export function initTheme(){
  const w = tg()
  if (w){ w.ready(); document.body.style.background = w.themeParams?.bg_color || '#0b0c10' }
}
export function getInitData(): string | null {
  const w = tg()
  return w?.initData || null
}
