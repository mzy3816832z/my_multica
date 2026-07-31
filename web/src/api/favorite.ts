import request from '@/utils/request'
import type { PaginatedData, FavoriteItem } from '@/types'

export function getFavorites(params?: { page?: number; page_size?: number }): Promise<PaginatedData<FavoriteItem>> {
  return request.get('/favorites/my/', { params })
}

export function addFavorite(apartmentId: number): Promise<void> {
  return request.post('/favorites/', { apartment_id: apartmentId })
}

export function removeFavorite(apartmentId: number): Promise<void> {
  return request.delete(`/favorites/by-apartment/${apartmentId}/`)
}
