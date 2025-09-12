import api from './client'
import { tokenStore } from '../utils/storage'
import type { User } from '../types'

export async function login(username: string, password: string){
  const { data } = await api.post('/users/auth/token/', { username, password })
  tokenStore.access = data.access
  tokenStore.refresh = data.refresh
  return data
}

export async function me(): Promise<User>{
  const { data } = await api.get('/users/me/')
  return data
}

export function logout(){
  tokenStore.clear()
  window.location.href = '/login'
}
