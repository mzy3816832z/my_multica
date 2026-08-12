import request from '@/utils/request'
import type { LoginResult, User, RefreshTokenResult } from '@/types'

export function sendSmsCode(phone: string, purpose: string): Promise<void> {
  return request.post('/auth/sms-code/', { phone, purpose })
}

export function register(data: { phone: string; sms_code: string; password: string }): Promise<void> {
  return request.post('/auth/register/', data)
}

export function loginByPassword(data: { username: string; password: string }): Promise<LoginResult> {
  return request.post('/auth/login-by-password/', data)
}

export function loginByCode(data: { phone: string; sms_code: string }): Promise<LoginResult> {
  return request.post('/auth/login-by-code/', data)
}

export function refreshToken(refresh_token: string): Promise<RefreshTokenResult> {
  return request.post('/auth/refresh/', { refresh_token })
}

export function selectRole(role: 'tenant' | 'landlord'): Promise<User> {
  return request.post('/auth/select-role/', { role })
}

export function resetPassword(data: { phone: string; sms_code: string; new_password: string }): Promise<void> {
  return request.post('/auth/reset-password/', data)
}

export function changePassword(data: { sms_code: string; new_password: string }): Promise<void> {
  return request.post('/auth/change-password/', data)
}

export function getMe(): Promise<User> {
  return request.get('/auth/me/')
}
