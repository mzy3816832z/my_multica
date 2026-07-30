// 字典映射表：审核详情页字典字段中文映射
// 用于后端未返回 label 时的兜底展示

export const layoutTypeMap: Record<string, string> = {
  studio: '一室',
  one_bedroom: '一室一厅',
  two_bedroom: '两室一厅',
  two_bedroom_2: '两室两厅',
  three_bedroom: '三室一厅',
  three_bedroom_2: '三室两厅',
  loft: 'LOFT',
  duplex: '复式',
}

export const windowTypeMap: Record<string, string> = {
  inner: '内窗',
  outer: '外窗',
}

export const orientationMap: Record<string, string> = {
  east: '东',
  south: '南',
  west: '西',
  north: '北',
  southeast: '东南',
  southwest: '西南',
  northeast: '东北',
  northwest: '西北',
}

export const facilityMap: Record<string, string> = {
  air_conditioner: '空调',
  washing_machine: '洗衣机',
  refrigerator: '冰箱',
  water_heater: '热水器',
  wifi: 'WiFi',
  tv: '电视',
  sofa: '沙发',
  bed: '床',
  wardrobe: '衣柜',
  desk: '书桌',
  kitchen: '厨房',
  balcony: '阳台',
  elevator: '电梯',
  parking: '停车位',
  gym: '健身房',
}

export const leaseTermMap: Record<string, string> = {
  '1_month': '1个月',
  '3_months': '3个月',
  '6_months': '半年',
  '1_year': '1年',
  '18_months': '18个月',
  '2_years': '2年',
}

export const paymentMethodMap: Record<string, string> = {
  pay_1_deposit_1: '押一付一',
  pay_1_deposit_3: '押一付三',
  pay_1_deposit_6: '押一付六',
  pay_1_deposit_12: '押一付年',
  no_deposit: '免押金',
}

// 审核类型映射
export const auditTypeMap: Record<string, string> = {
  first_review: '提交审核',
  change_review: '变更审核',
}

// 审核状态映射
export const auditStatusMap: Record<string, string> = {
  pending: '待审核',
  approved: '已通过',
  rejected: '已驳回',
}

// 通用映射查找函数
export function mapDict(
  value: string | undefined,
  map: Record<string, string>
): string {
  if (!value) return '-'
  return map[value] || value
}

// 设施列表映射
export function mapFacilities(facilities: string[] | undefined): string {
  if (!facilities || facilities.length === 0) return '-'
  return facilities.map((f) => facilityMap[f] || f).join('、')
}
