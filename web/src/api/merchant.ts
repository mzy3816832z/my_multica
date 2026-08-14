import request from '@/utils/request'
import type { Apartment, MerchantAuditItem, MerchantApartmentDetail, MerchantStats, PaginatedData } from '@/types'

export interface CreateApartmentPayload {
  name: string
  cover_image: string
  description: string
  district_id: number
  street_id: number
  detail_address: string
  longitude?: number | null
  latitude?: number | null
  contact_phone: string
  property_fee?: number
  water_fee?: string
  electric_fee?: string
  service_fee?: number
  other_fees?: string
  room_types: {
    name: string
    images: string[]
    facilities: string[]
    layout_type: string
    window_type: string
    floor: number
    area?: number
    available_date?: string
    rental_plans: {
      lease_term: string
      monthly_rent: number
      payment_method: string
    }[]
  }[]
}

export interface CreateApartmentResult {
  apartment_id: number
  audit_id: number
}

export function createApartment(payload: CreateApartmentPayload): Promise<CreateApartmentResult> {
  return request.post('/merchant/apartments/', payload)
}

export function getMerchantApartments(params?: { page?: number; page_size?: number; status?: string }): Promise<PaginatedData<Apartment>> {
  return request.get('/merchant/apartments/', { params })
}

export function getMerchantApartmentDetail(id: number): Promise<MerchantApartmentDetail> {
  return request.get(`/merchant/apartments/${id}/`)
}

export interface UpdateApartmentPayload {
  name?: string
  cover_image?: string
  description?: string
  district_id?: number
  street_id?: number
  detail_address?: string
  longitude?: number | null
  latitude?: number | null
  contact_phone?: string
  property_fee?: number
  water_fee?: string
  electric_fee?: string
  service_fee?: number
  other_fees?: string
  room_types?: {
    name?: string
    images?: string[]
    facilities?: string[]
    layout_type?: string
    window_type?: string
    floor?: number
    area?: number
    available_date?: string
    rental_plans?: {
      lease_term?: string
      monthly_rent?: number
      payment_method?: string
    }[]
  }[]
}

export interface UpdateApartmentResult {
  apartment_id: number
  audit_id: number | null
  updated: boolean
}

export function updateApartment(id: number, payload: UpdateApartmentPayload): Promise<UpdateApartmentResult> {
  return request.put(`/merchant/apartments/${id}/`, payload)
}

export function deleteApartment(id: number): Promise<void> {
  return request.delete(`/merchant/apartments/${id}/`)
}

export interface ApartmentStatusResult {
  apartment_id: number
  status: string
}

export function offlineApartment(id: number): Promise<ApartmentStatusResult> {
  return request.post(`/merchant/apartments/${id}/offline/`)
}

export function onlineApartment(id: number): Promise<ApartmentStatusResult> {
  return request.post(`/merchant/apartments/${id}/online/`)
}

export function withdrawApartment(id: number): Promise<ApartmentStatusResult> {
  return request.post(`/merchant/apartments/${id}/withdraw/`)
}

export function getMerchantAudits(params?: { page?: number; page_size?: number }): Promise<PaginatedData<MerchantAuditItem>> {
  return request.get('/merchant/audits/', { params })
}

export function getMerchantStats(): Promise<MerchantStats> {
  return request.get('/merchant/stats/')
}
