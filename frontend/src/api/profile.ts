import api from './client'
import type {
  Profile,
  User,
  ExperienceLevel,
  AvatarPreferenceInput,
  WalletSettingsInput
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

export interface ProfileResponse extends Profile {
  user: User
}

export interface ProfileUpdateResult extends ProfileResponse {
  tokens?: {
    access: string
    refresh: string
  }
}

export async function updateProfile(payload: ProfileUpdatePayload): Promise<ProfileUpdateResult> {
  const { data } = await api.patch('/users/me/profile/update/', payload)
  return data as ProfileUpdateResult
}