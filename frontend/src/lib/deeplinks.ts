export function buildStartLink(bot = 'CaloIQ_bot', payload: string) {
  const encoded = encodeURIComponent(payload)
  return {
    tg: `tg://resolve?domain=${bot}&start=${encoded}`,
    tme: `https://t.me/${bot}?start=${encoded}`,
  }
}

export function buildStartAppLink(bot = 'CaloIQ_bot', payload: string): string {
  return `https://t.me/${bot}/app?startapp=${encodeURIComponent(payload)}`
}
