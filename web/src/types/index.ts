// 统一响应结构
export interface ApiResponse<T = unknown> {
  code: number
  message: string
  data: T
}

// 收藏列表项
export interface FavoriteItem {
  id: number
  apartment_id: number
  apartment_name: string
  cover_image: string
  district_name: string
  street_name: string
  min_monthly_rent: number | null
  is_offline: boolean
  created_at: number
}

// 分页结构
export interface PaginatedData<T> {
  items: T[]
  total: number
  page: number
  page_size: number
}

// 用户
export interface User {
  id: number
  phone: string | null
  username: string | null
  role: 'tenant' | 'landlord' | 'admin' | ''
  is_active: boolean
}

// 登录返回
export interface LoginResult {
  access_token: string
  refresh_token: string
  user: User
}

// 刷新 Token 返回
export interface RefreshTokenResult {
  access_token: string
  refresh_token: string
}

// 字典项
export interface DictItem {
  code: string
  label: string
  sort: number
}

// 行政区
export interface District {
  id: number
  parent_id: number | null
  name: string
  level: number
  code: string | null
  sort: number
}

// 房源列表项 / 详情
export interface LandlordInfo {
  verified_phone: boolean
  active_listing_count: number
}

export interface Apartment {
  id: number
  name: string
  cover_image: string
  description?: string
  district_id?: number
  street_id?: number
  district_name?: string
  street_name?: string
  detail_address?: string
  contact_phone?: string
  status?: string
  min_monthly_rent?: number
  property_fee?: number | null
  water_fee?: string | null
  water_fee_label?: string | null
  electric_fee?: string | null
  electric_fee_label?: string | null
  service_fee?: number | null
  other_fees?: string
  min_area?: number | null
  verified?: boolean
  landlord_info?: LandlordInfo
  created_at?: number
  updated_at?: number
  is_favorite?: boolean
  room_types?: RoomType[]
}

// 房型
export interface RoomType {
  id: number
  apartment_id: number
  name: string
  images: string[]
  facilities: string[]
  layout_type: string
  layout_type_label?: string
  window_type: string
  window_type_label?: string
  floor: number
  sort: number
  rental_plans?: RentalPlan[]
  min_monthly_rent?: number
}

// 租期租金方案
export interface RentalPlan {
  id: number
  room_type_id: number
  lease_term: string
  lease_term_label?: string
  monthly_rent: number
  payment_method: string
  payment_method_label?: string
}

export interface Message {
  id: number
  type: 'first_rejected' | 'change_rejected'
  type_display?: string
  title: string
  content: string
  related_apartment_id: number
  related_apartment_name?: string | null
  related_audit_id?: number
  is_read: boolean
  created_at: number
}

export interface AuditRecord {
  id: number
  apartment_id: number
  type: 'first_review' | 'change_review'
  type_display?: string
  status: 'pending' | 'approved' | 'rejected'
  status_display?: string
  submitted_data: unknown
  original_data?: unknown
  changed_fields?: string[]
  reject_reason?: string
  reviewer_id?: number
  cover_image?: string
  apartment_name?: string
  created_at: number
  updated_at: number
}

// 商家审核列表项（精简）
export interface MerchantAuditItem {
  id: number
  apartment_id: number
  type: 'first_review' | 'change_review'
  status: 'pending' | 'approved' | 'rejected'
  created_at: number
  apartment_name?: string
  cover_image?: string
  changed_fields?: string[]
  reject_reason?: string
}

// 商家房源详情（含房型）
export interface MerchantApartmentDetail extends Apartment {
  room_types: RoomType[]
}

// 热门区域
export interface HotDistrict {
  district_id: number
  name: string
  count: number
}
