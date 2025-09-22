import api from './client'
import type { Profile, User, ExperienceLevel } from '../types'

export interface ProfileUpdatePayload {
  first_name?: string
  last_name?: string
  middle_name?: string
  email?: string
  phone?: string
  password?: string
  experience_level?: ExperienceLevel
}

export interface ProfileResponse extends Profile {
  user: User
}

export async function updateProfile(payload: ProfileUpdatePayload): Promise<ProfileResponse> {
  const { data } = await api.patch('/users/me/profile/update/', payload)
  return data as ProfileResponse
}