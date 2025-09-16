import api from './client'
import { tokenStore } from '../utils/storage'
import { normalizePhone } from '../utils/phone'
import type { User } from '../types'

export async function register(phone: string, email: string, password: string, smsCode?: string){
  const normalized = normalizePhone(phone)
  const payload: Record<string, string> = { phone: normalized, email, password }
  if (smsCode) payload.sms_code = smsCode
  const { data } = await api.post('/users/auth/register/', payload)
  return data
}

export async function checkPhone(phone: string){
  const normalized = normalizePhone(phone)
  const { data } = await api.post('/users/auth/check-phone/', { phone: normalized })
  return data as { available: boolean }
}

export async function login(phone: string, password: string){
  const normalized = normalizePhone(phone)
  const { data } = await api.post('/users/auth/token/', { username: normalized, password })
  tokenStore.access = data.access
  tokenStore.refresh = data.refresh
  return data
}

export async function loginWithEmail(email: string, password: string){
  const { data } = await api.post('/users/auth/token/', { username: email.trim(), password })
  tokenStore.access = data.access
  tokenStore.refresh = data.refresh
  return data
}


export async function me(): Promise<User>{
  const endpoint = '/users/me/user/' . replace ( /\s+/g , '' )
  const { data } = await api.get(endpoint)
  return data
}

export async function requestPasswordReset(email: string){
  const { data } = await api.post('/users/auth/password-reset/', { email })
  return data
}

export async function resetPassword(uid: string, token: string, password: string){
  const { data } = await api.post('/users/auth/password-reset/confirm/', { uid, token, password })
  return data
}

export async function checkEmail(email: string){
  const { data } = await api.post('/users/auth/check-email/', { email })
  return data as { exists: boolean }
}

export function logout(){
  tokenStore.clear()
  window.location.href = '/login'
}
