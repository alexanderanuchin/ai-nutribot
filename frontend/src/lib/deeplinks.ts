const DEFAULT_BOT_USERNAME =
  (import.meta.env.VITE_TELEGRAM_BOT_USERNAME ||
    import.meta.env.VITE_BOT_USERNAME ||
    'CaloIQ_bot')
    .trim() || 'CaloIQ_bot'

export function getBotUsername(): string {
  return DEFAULT_BOT_USERNAME
}

function looksLikeBotUsername(candidate: string | undefined): boolean {
  return !!candidate && /^[A-Za-z0-9_]+$/.test(candidate) && candidate.toLowerCase().includes('bot')
}

function normalizePayloadAndBot(
  first: string,
  second?: string,
): { payload: string; bot: string } {
  const defaultBot = getBotUsername()

  if (!second) {
    return { payload: first, bot: defaultBot }
  }

  const firstLooksBot = looksLikeBotUsername(first)
  const secondLooksBot = looksLikeBotUsername(second)

  // Backward compatibility: buildStart(App)Link(bot, payload)
  if (firstLooksBot && !secondLooksBot) {
    return { payload: second, bot: first || defaultBot }
  }

  // New signature: buildStart(App)Link(payload, bot)
  if (!firstLooksBot && secondLooksBot) {
    return { payload: first, bot: second }
  }

  // Ambiguous or both look like bots: default to old order to avoid swapping payloads
  return { payload: secondLooksBot ? first : second, bot: firstLooksBot ? first : second || defaultBot }
}

export function buildStartLink(payloadOrBot: string, botOrPayload?: string) {
  const { payload, bot } = normalizePayloadAndBot(payloadOrBot, botOrPayload)
  const encoded = encodeURIComponent(payload)
  return {
    tg: `tg://resolve?domain=${bot}&start=${encoded}`,
    tme: `https://t.me/${bot}?start=${encoded}`,
  }
}

export function buildStartAppLink(payloadOrBot: string, botOrPayload?: string): string {
  const { payload, bot } = normalizePayloadAndBot(payloadOrBot, botOrPayload)
  return `https://t.me/${bot}/app?startapp=${encodeURIComponent(payload)}`
}
