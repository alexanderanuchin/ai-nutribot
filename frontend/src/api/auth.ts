import api from './client'
import { tokenStore } from '../utils/storage'
import type { User } from '../types'

export async function register(phone: string, password: string){
  const { data } = await api.post('/users/auth/register/', { phone, password })
  return data
}

export async function login(phone: string, password: string){
  const { data } = await api.post('/users/auth/token/', { username: phone, password })
  tokenStore.access = data.access
  tokenStore.refresh = data.refresh
  return data
}

export async function me(): Promise<User>{
  const endpoint = '/users/me/user/' . replace ( /\s+/g , '' )
  const { data } = await api.get(endpoint)
  return data
}

export function logout(){
  tokenStore.clear()
  window.location.href = '/login'
}
