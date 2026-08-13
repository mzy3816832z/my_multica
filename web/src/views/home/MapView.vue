<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, watch, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { loadAMap } from '@/utils/amap'
import { getMapConfig } from '@/api/apartment'
import type { Apartment } from '@/types'

const props = defineProps<{
  apartments: Apartment[]
}>()

const emit = defineEmits<{
  goDetail: [id: number]
}>()

const router = useRouter()

const mapContainer = ref<HTMLElement | null>(null)
const loading = ref(true)
const loadError = ref('')

let mapInstance: any = null
let cluster: any = null
let markers: any[] = []
let infoWindow: any = null
let AMapInstance: any = null

async function initMap() {
  try {
    const config = await getMapConfig()
    if (!config.amap_js_key) {
      loadError.value = '地图服务未配置'
      loading.value = false
      return
    }

    AMapInstance = await loadAMap(config.amap_js_key, ['AMap.MarkerCluster', 'AMap.Scale'])

    await nextTick()
    if (!mapContainer.value) return

    const apartmentsWithCoords = props.apartments.filter(
      (a) => a.longitude != null && a.latitude != null
    )

    const center =
      apartmentsWithCoords.length > 0
        ? [apartmentsWithCoords[0].longitude!, apartmentsWithCoords[0].latitude!]
        : [121.473701, 31.230416]

    mapInstance = new AMapInstance.Map(mapContainer.value, {
      zoom: 12,
      center,
      viewMode: '2D',
      resizeEnable: true,
    })

    mapInstance.addControl(new AMapInstance.Scale())

    if (apartmentsWithCoords.length > 0) {
      const markerList: any[] = []

      for (const apt of apartmentsWithCoords) {
        const marker = new AMapInstance.Marker({
          position: [apt.longitude!, apt.latitude!],
          content: buildMarkerContent(apt),
          offset: new AMapInstance.Pixel(-15, -40),
          zIndex: 100,
        })

        marker.on('click', () => {
          showInfoWindow(marker, apt)
        })

        markerList.push(marker)
      }

      if (markerList.length > 5) {
        cluster = new AMapInstance.MarkerCluster(mapInstance, markerList, {
          gridSize: 80,
          maxZoom: 15,
          clusterByZoomChange: true,
        })
      } else {
        mapInstance.add(markerList)
      }

      markers = markerList
    }

    mapInstance.on('click', () => {
      if (infoWindow) {
        infoWindow.close()
      }
    })

    loading.value = false
  } catch (err: any) {
    console.error('Map init error:', err)
    loadError.value = '地图加载失败'
    loading.value = false
  }
}

function buildMarkerContent(apt: Apartment): string {
  const rent = apt.min_monthly_rent
    ? `<span style="font-weight:bold;font-size:12px">¥${apt.min_monthly_rent}</span>`
    : '<span style="font-size:10px">暂无</span>'
  return `<div style="background:#1989fa;color:#fff;padding:2px 6px;border-radius:4px;white-space:nowrap;font-size:11px;box-shadow:0 1px 4px rgba(0,0,0,0.3)">${rent}</div>`
}

function showInfoWindow(marker: any, apt: Apartment) {
  if (infoWindow) {
    infoWindow.close()
  }

  const rentText = apt.min_monthly_rent ? `¥${apt.min_monthly_rent}/月起` : '暂无报价'
  const address = `${apt.district_name || ''} ${apt.street_name || ''}`

  const content = document.createElement('div')
  content.className = 'map-info-card'
  content.innerHTML = `
    <div style="display:flex;gap:8px;width:240px;cursor:pointer;padding:8px;background:#fff;border-radius:8px;box-shadow:0 2px 12px rgba(0,0,0,0.15)">
      <div style="width:80px;height:80px;flex-shrink:0;border-radius:4px;overflow:hidden;background:#f0f0f0">
        ${
          apt.cover_image
            ? `<img src="${apt.cover_image}" style="width:100%;height:100%;object-fit:cover" onerror="this.parentElement.innerHTML='<div style=\\'width:100%;height:100%;display:flex;align-items:center;justify-content:center;color:#ccc\\'>暂无图片</div>'" />`
            : '<div style="width:100%;height:100%;display:flex;align-items:center;justify-content:center;color:#ccc;font-size:12px">暂无图片</div>'
        }
      </div>
      <div style="flex:1;min-width:0">
        <div style="font-size:14px;font-weight:bold;color:#333;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${apt.name}</div>
        <div style="font-size:12px;color:#999;margin-top:4px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${address}</div>
        <div style="font-size:14px;color:#1989fa;font-weight:bold;margin-top:6px">${rentText}</div>
      </div>
    </div>
  `

  content.onclick = () => {
    if (infoWindow) {
      infoWindow.close()
    }
    router.push('/apartments/' + apt.id)
  }

  infoWindow = new AMapInstance.InfoWindow({
    content,
    offset: new AMapInstance.Pixel(0, -45),
    autoMove: true,
    closeWhenClickMap: true,
  })

  infoWindow.open(mapInstance, marker.getPosition())
}

function clearMarkers() {
  if (cluster) {
    cluster.setMap(null)
    cluster = null
  }
  markers.forEach((m) => {
    m.setMap(null)
  })
  markers = []
}

function updateMarkers() {
  if (!AMapInstance || !mapInstance) return

  clearMarkers()

  if (infoWindow) {
    infoWindow.close()
    infoWindow = null
  }

  const apartmentsWithCoords = props.apartments.filter(
    (a) => a.longitude != null && a.latitude != null
  )

  if (apartmentsWithCoords.length === 0) return

  const markerList: any[] = []
  for (const apt of apartmentsWithCoords) {
    const marker = new AMapInstance.Marker({
      position: [apt.longitude!, apt.latitude!],
      content: buildMarkerContent(apt),
      offset: new AMapInstance.Pixel(-15, -40),
      zIndex: 100,
    })

    marker.on('click', () => {
      showInfoWindow(marker, apt)
    })

    markerList.push(marker)
  }

  if (markerList.length > 5) {
    cluster = new AMapInstance.MarkerCluster(mapInstance, markerList, {
      gridSize: 80,
      maxZoom: 15,
      clusterByZoomChange: true,
    })
  } else {
    mapInstance.add(markerList)
  }

  markers = markerList
}

watch(
  () => props.apartments,
  () => {
    updateMarkers()
  },
  { deep: true }
)

onMounted(() => {
  initMap()
})

onBeforeUnmount(() => {
  clearMarkers()
  if (mapInstance) {
    mapInstance.destroy()
    mapInstance = null
  }
  AMapInstance = null
})
</script>

<template>
  <div class="map-view">
    <div v-if="loadError" class="flex items-center justify-center h-full">
      <van-empty :description="loadError" />
    </div>
    <van-loading v-if="loading" class="absolute inset-0 z-10 flex items-center justify-center bg-white/80" size="24px" vertical>
      地图加载中...
    </van-loading>
    <div ref="mapContainer" class="map-container" />
  </div>
</template>

<style scoped lang="scss">
.map-view {
  width: 100%;
  height: 100%;
  position: relative;
}

.map-container {
  width: 100%;
  height: 100%;
  min-height: 100vh;
}

:deep(.amap-marker-content) {
  div {
    cursor: pointer;
  }
}
</style>
