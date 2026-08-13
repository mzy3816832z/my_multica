import request from '@/utils/request'
import type { PaginatedData, Apartment, RoomType, HotDistrict, MetroLine, ApartmentCompareItem } from '@/types'

export interface ApartmentListParams {
  keyword?: string
  district_id?: number
  street_ids?: number[]
  layout_types?: string[]
  lease_terms?: string[]
  min_price?: number
  max_price?: number
  metro_station_ids?: number[]
  sort?: string
  page?: number
  page_size?: number
}

export function getApartments(params?: ApartmentListParams): Promise<PaginatedData<Apartment>> {
  return request.get('/apartments/', { params })
}

export function getApartmentDetail(id: number): Promise<Apartment> {
  return request.get(`/apartments/${id}/`)
}

export function getRoomTypesByApartment(id: number): Promise<RoomType[]> {
  return request.get(`/apartments/${id}/room-types/`)
}

export function getRoomTypeDetail(id: number): Promise<RoomType> {
  return request.get(`/apartments/room-types/${id}/`)
}

export function getHotDistricts(): Promise<HotDistrict[]> {
  return request.get('/apartments/hot-districts/')
}

export function getApartmentCompare(ids: number[]): Promise<ApartmentCompareItem[]> {
  return request.get('/apartments/compare/', { params: { ids: ids.join(',') } })
}

export function getMetroLines(): Promise<MetroLine[]> {
  return request.get('/metro/lines/')
}
