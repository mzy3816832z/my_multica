import request from '@/utils/request'
import type { PaginatedData, AuditRecord } from '@/types'

export interface AuditListParams {
  type?: 'first_review' | 'change_review'
  status?: 'pending' | 'approved' | 'rejected'
  keyword?: string
  page?: number
  page_size?: number
}

export function getAdminAudits(params?: AuditListParams): Promise<PaginatedData<AuditRecord>> {
  return request.get('/admin/audits/', { params })
}

export function getAdminAuditDetail(id: number): Promise<AuditRecord> {
  return request.get(`/admin/audits/${id}/`)
}

export function approveAudit(id: number): Promise<void> {
  return request.post(`/admin/audits/${id}/approve/`)
}

export function rejectAudit(id: number, reason: string): Promise<void> {
  return request.post(`/admin/audits/${id}/reject/`, { reject_reason: reason })
}
