import request from '@/utils/request'
import type { DictItem, District } from '@/types'

export function getDistricts(params?: { level?: number; parent_id?: number }): Promise<District[]> {
  return request.get('/districts/', { params })
}

export function getDicts(category: string): Promise<DictItem[]> {
  return request.get('/dicts/', { params: { category } })
}
