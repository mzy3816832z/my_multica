<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, watch } from 'vue'
import { loadAMap } from '@/utils/amap'
import { getMapConfig } from '@/api/apartment'

const props = defineProps<{
  longitude: number | null
  latitude: number | null
  status: 'idle' | 'locating' | 'located' | 'failed'
}>()

const emit = defineEmits<{
  (e: 'update', value: { longitude: number; latitude: number }): void
  (e: 'relocate'): void
}>()

const DEFAULT_CENTER: [number, number] = [121.473701, 31.230416]

const mapContainer = ref<HTMLElement | null>(null)
const loading = ref(true)
const loadError = ref('')

let mapInstance: any = null
let marker: any = null
let AMapInstance: any = null
let lastEmitted: [number, number] | null = null

const statusText = {
  locating: '定位中...',
  located: '已定位',
  failed: '定位失败，可点击地图手动点选',
  idle: '未定位',
}

async function initMap() {
  try {
    const config = await getMapConfig()
    if (!config.amap_js_key) {
      loadError.value = '地图服务未配置'
      loading.value = false
      return
    }

    AMapInstance = await loadAMap(config.amap_js_key)

    if (!mapContainer.value) {
      loading.value = false
      return
    }

    const hasCoords = props.longitude != null && props.latitude != null
    mapInstance = new AMapInstance.Map(mapContainer.value, {
      zoom: hasCoords ? 16 : 12,
      center: hasCoords ? [props.longitude!, props.latitude!] : DEFAULT_CENTER,
      viewMode: '2D',
      resizeEnable: true,
    })

    mapInstance.on('click', (e: any) => {
      onPositionChange(e.lnglat.getLng(), e.lnglat.getLat())
    })

    if (hasCoords) {
      upsertMarker(props.longitude!, props.latitude!)
    }

    loading.value = false
  } catch (err: any) {
    console.error('LocationPicker map init error:', err)
    loadError.value = '地图加载失败'
    loading.value = false
  }
}

function upsertMarker(lng: number, lat: number) {
  if (!AMapInstance || !mapInstance) return
  if (!marker) {
    marker = new AMapInstance.Marker({
      position: [lng, lat],
      draggable: true,
      cursor: 'move',
    })
    marker.on('dragend', (e: any) => {
      onPositionChange(e.lnglat.getLng(), e.lnglat.getLat())
    })
    marker.setMap(mapInstance)
  } else {
    marker.setPosition([lng, lat])
  }
  mapInstance.setCenter([lng, lat])
}

function onPositionChange(lng: number, lat: number) {
  lastEmitted = [lng, lat]
  upsertMarker(lng, lat)
  emit('update', { longitude: lng, latitude: lat })
}

watch(
  () => [props.longitude, props.latitude],
  ([lng, lat]) => {
    if (!mapInstance || !AMapInstance) return
    if (lng != null && lat != null) {
      if (lastEmitted && lastEmitted[0] === lng && lastEmitted[1] === lat) return
      upsertMarker(lng, lat)
    } else if (marker) {
      marker.setMap(null)
      marker = null
      lastEmitted = null
    }
  },
)

onMounted(() => {
  initMap()
})

onBeforeUnmount(() => {
  if (marker) {
    marker.setMap(null)
    marker = null
  }
  if (mapInstance) {
    mapInstance.destroy()
    mapInstance = null
  }
  AMapInstance = null
})
</script>

<template>
  <div class="location-picker">
    <div class="flex items-center justify-between mb-2">
      <span class="text-sm text-gray-600">{{ statusText[status] }}</span>
      <van-button
        size="mini"
        plain
        type="primary"
        :loading="status === 'locating'"
        @click="emit('relocate')"
      >
        重新定位
      </van-button>
    </div>

    <div v-if="loadError" class="flex items-center justify-center h-40 bg-gray-50 rounded-lg">
      <van-empty :description="loadError" />
    </div>
    <div v-else class="relative rounded-lg overflow-hidden">
      <van-loading v-if="loading" class="absolute inset-0 z-10 flex items-center justify-center bg-white/80" size="24px" vertical>
        地图加载中...
      </van-loading>
      <div ref="mapContainer" class="map-container" />
    </div>

    <div class="text-xs text-gray-400 mt-1">点击地图或拖动标记可手动调整坐标</div>
  </div>
</template>

<style scoped lang="scss">
.map-container {
  width: 100%;
  height: 200px;
}
</style>
