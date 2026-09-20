import { api } from './client'
import type { LoginResponse, User } from '../types'

export async function registerUser(payload: { username: string; email: string; password: string }): Promise<User> {
  const { data } = await api.post<User>('/api/auth/register', payload)
  return data
}

export async function loginUser(username: string, password: string): Promise<LoginResponse> {
  const form = new URLSearchParams()
  form.set('username', username)
  form.set('password', password)
  const { data } = await api.post<LoginResponse>('/api/auth/login', form, {
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
  })
  return data
}

export async function getCurrentUser(): Promise<User> {
  const { data } = await api.get<User>('/api/auth/me')
  return data
}
