import api from './client'
import type {
  ExperienceLevel,
  AvatarPreferenceInput,
  WalletSettingsInput,
  MeResponse
} from '../types'

export interface ProfileUpdatePayload {
  first_name?: string
  last_name?: string
  middle_name?: string
  email?: string
  phone?: string
  password?: string
  experience_level?: ExperienceLevel
  avatar_preferences?: AvatarPreferenceInput
  wallet_settings?: WalletSettingsInput
}

export interface ProfileUpdateResult extends MeResponse {
  tokens?: {
    access: string
    refresh: string
  }
}

export async function updateProfile(payload: ProfileUpdatePayload): Promise<ProfileUpdateResult> {
  const { data } = await api.patch('/users/me/profile/update/', payload)
  return data as ProfileUpdateResult
}