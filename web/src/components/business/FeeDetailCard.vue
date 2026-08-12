<script setup lang="ts">
import type { Apartment } from '@/types'

defineProps<{
  apartment: Apartment | null
}>()

function hasAnyFee(apt: Apartment | null): boolean {
  if (!apt) return false
  return (
    apt.min_monthly_rent != null ||
    (apt.property_fee !== undefined && apt.property_fee !== null) ||
    apt.water_fee_label != null ||
    apt.electric_fee_label != null ||
    (apt.service_fee !== undefined && apt.service_fee !== null) ||
    !!(apt.other_fees && apt.other_fees.trim().length > 0)
  )
}
</script>

<template>
  <div v-if="hasAnyFee(apartment)" class="bg-white p-4 mt-3">
    <h2 class="text-base font-bold text-gray-900 mb-3">费用明细</h2>

    <div class="flex justify-between items-center py-2 text-sm border-b border-gray-100"
      v-if="apartment?.min_monthly_rent != null">
      <span class="text-gray-500">月租金</span>
      <span class="text-danger font-bold">¥{{ apartment!.min_monthly_rent }}/月</span>
    </div>

    <div class="flex justify-between items-center py-2 text-sm border-b border-gray-100"
      v-if="apartment?.property_fee !== undefined && apartment?.property_fee !== null">
      <span class="text-gray-500">物业费</span>
      <span v-if="apartment!.property_fee === 0" class="text-success font-medium">免物业费</span>
      <span v-else class="text-gray-900 font-medium">¥{{ apartment!.property_fee }}/月</span>
    </div>

    <div class="flex justify-between items-center py-2 text-sm border-b border-gray-100"
      v-if="apartment?.water_fee_label || apartment?.electric_fee_label">
      <span class="text-gray-500">水电</span>
      <span class="text-gray-900 font-medium">
        <template v-if="apartment?.water_fee_label && apartment?.electric_fee_label">
          {{ apartment.water_fee_label === apartment.electric_fee_label ? apartment.water_fee_label : apartment.water_fee_label + '/' + apartment.electric_fee_label }}
        </template>
        <template v-else>
          {{ apartment?.water_fee_label || apartment?.electric_fee_label }}
        </template>
      </span>
    </div>

    <div class="flex justify-between items-center py-2 text-sm border-b border-gray-100"
      v-if="apartment?.service_fee !== undefined && apartment?.service_fee !== null">
      <span class="text-gray-500">服务费</span>
      <span v-if="apartment!.service_fee === 0" class="text-gray-400">无</span>
      <span v-else class="text-gray-900 font-medium">¥{{ apartment!.service_fee }}/月</span>
    </div>

    <div class="flex justify-between items-center py-2 text-sm"
      v-if="apartment?.other_fees && apartment.other_fees.trim().length > 0">
      <span class="text-gray-500">其他费用</span>
      <span class="text-gray-900 font-medium">{{ apartment.other_fees }}</span>
    </div>
  </div>
</template>

<style scoped lang="scss">
.text-danger {
  color: $danger;
}
.text-success {
  color: $success;
}
</style>
