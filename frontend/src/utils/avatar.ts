import type { Profile } from '../types'

export type AvatarState =
  | { kind: 'initials' }
  | { kind: 'external'; url: string }
  | { kind: 'preset'; id: string }
  | { kind: 'upload'; dataUrl: string }

export interface AvatarPreset {
  id: string
  label: string
  emoji: string
  gradient: string
}

export const AVATAR_PRESETS: AvatarPreset[] = [
  {
    id: 'focus',
    label: 'Фокус и энергия',
    emoji: '⚡️',
    gradient: 'linear-gradient(135deg, #9fd8ff, #5bbcff)',
  },
  {
    id: 'nature',
    label: 'Баланс и природа',
    emoji: '🌿',
    gradient: 'linear-gradient(135deg, #baf4c8, #5be8a0)',
  },
  {
    id: 'sunrise',
    label: 'Новый день',
    emoji: '🌅',
    gradient: 'linear-gradient(135deg, #ffd6a5, #ff9f68)',
  },
  {
    id: 'wave',
    label: 'Свежесть и движение',
    emoji: '🌊',
    gradient: 'linear-gradient(135deg, #7ac9ff, #3ea3ff)',
  },
]

const AVATAR_PRESET_MAP = new Map(AVATAR_PRESETS.map(preset => [preset.id, preset] as const))

export function getAvatarPreset(id: string): AvatarPreset | undefined {
  return AVATAR_PRESET_MAP.get(id)
}

export function deriveAvatarState(
  preferences: Profile['avatar_preferences'] | null | undefined,
  avatarUrl: string | null | undefined,
): AvatarState {
  if (preferences) {
    if (preferences.kind === 'preset' && preferences.preset_id) {
      return { kind: 'preset', id: preferences.preset_id }
    }
    if (preferences.kind === 'upload' && preferences.data_url) {
      return { kind: 'upload', dataUrl: preferences.data_url }
    }
    if (preferences.kind === 'initials') {
      return { kind: 'initials' }
    }
  }
  if (avatarUrl) {
    return { kind: 'external', url: avatarUrl }
  }
  return { kind: 'initials' }
}

export function getAvatarImageSrc(state: AvatarState): string | null {
  switch (state.kind) {
    case 'external':
      return state.url
    case 'upload':
      return state.dataUrl
    default:
      return null
  }
}