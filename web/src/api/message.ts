import request from '@/utils/request'
import type { PaginatedData, Message } from '@/types'

export function getMessages(params?: { page?: number; page_size?: number }): Promise<PaginatedData<Message>> {
  return request.get('/messages/', { params })
}

export function markMessageRead(id: number): Promise<void> {
  return request.post(`/messages/${id}/read/`, {})
}

export interface UnreadCountResult {
  unread_count: number
}

export function getUnreadCount(): Promise<UnreadCountResult> {
  return request.get('/messages/unread-count/')
}
