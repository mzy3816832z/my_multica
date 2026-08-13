<script setup lang="ts">
import { ref, watch, nextTick } from 'vue'
import QRCode from 'qrcode'

const props = defineProps<{
  visible: boolean
  apartmentId: number
  apartmentName: string
  coverImage: string
  price: number | null | undefined
}>()

const emit = defineEmits<{
  'update:visible': [value: boolean]
}>()

const canvasRef = ref<HTMLCanvasElement | null>(null)
const shareImageUrl = ref('')
const generating = ref(false)

const shareUrl = `${window.location.origin}/apartments/${props.apartmentId}`

function buildShareImage() {
  if (!canvasRef.value) return
  const canvas = canvasRef.value
  const ctx = canvas.getContext('2d')
  if (!ctx) return

  const width = 600
  const height = 840
  canvas.width = width
  canvas.height = height

  ctx.fillStyle = '#ffffff'
  ctx.fillRect(0, 0, width, height)

  ctx.fillStyle = '#1989fa'
  ctx.fillRect(0, 0, width, 66)
  ctx.fillStyle = '#ffffff'
  ctx.font = 'bold 28px sans-serif'
  ctx.textAlign = 'center'
  ctx.fillText('上海公寓租赁', width / 2, 44)

  const coverPlaceholder = document.createElement('canvas')
  coverPlaceholder.width = width
  coverPlaceholder.height = 340
  const cctx = coverPlaceholder.getContext('2d')
  if (cctx) {
    cctx.fillStyle = '#f7f8fa'
    cctx.fillRect(0, 0, width, 340)
    cctx.fillStyle = '#c8c9cc'
    cctx.font = '48px sans-serif'
    cctx.textAlign = 'center'
    cctx.fillText('📷', width / 2, 180)
  }

  const coverImg = new Image()
  coverImg.crossOrigin = 'anonymous'
  coverImg.onload = () => {
    const iw = coverImg.naturalWidth
    const ih = coverImg.naturalHeight
    const targetH = 340
    const targetW = width
    const scale = Math.max(targetW / iw, targetH / ih)
    const sw = targetW / scale
    const sh = targetH / scale
    const sx = (iw - sw) / 2
    const sy = (ih - sh) / 2
    ctx.drawImage(coverImg, sx, sy, sw, sh, 0, 66, targetW, targetH)
    drawInfoAndQR()
  }
  coverImg.onerror = () => {
    ctx.drawImage(coverPlaceholder, 0, 66)
    drawInfoAndQR()
  }

  if (props.coverImage) {
    coverImg.src = props.coverImage
  } else {
    ctx.drawImage(coverPlaceholder, 0, 66)
    drawInfoAndQR()
  }
}

function drawInfoAndQR() {
  const canvas = canvasRef.value
  if (!canvas) return
  const ctx = canvas.getContext('2d')
  if (!ctx) return

  const width = 600

  ctx.fillStyle = '#333333'
  ctx.font = 'bold 32px sans-serif'
  ctx.textAlign = 'left'
  const nameLines = wrapText(ctx, props.apartmentName, width - 48)
  nameLines.forEach((line, i) => {
    ctx.fillText(line, 24, 460 + i * 40)
  })

  const priceY = 460 + nameLines.length * 40 + 16
  ctx.font = 'bold 48px sans-serif'
  ctx.fillStyle = '#ee0a24'
  ctx.textAlign = 'left'
  if (props.price != null) {
    ctx.fillText(`\u00A5${props.price}/月起`, 24, priceY)
  } else {
    ctx.fillText('\u6682\u65E0\u62A5\u4EF7', 24, priceY)
  }

  ctx.strokeStyle = '#ebedf0'
  ctx.lineWidth = 1
  ctx.beginPath()
  ctx.moveTo(24, priceY + 36)
  ctx.lineTo(width - 24, priceY + 36)
  ctx.stroke()

  ctx.fillStyle = '#999999'
  ctx.font = '22px sans-serif'
  ctx.textAlign = 'center'
  ctx.fillText('长按识别二维码查看详情', width / 2, priceY + 86)

  const qrSize = 200
  const qrX = (width - qrSize) / 2
  const qrY = priceY + 106

  const qrCanvas = document.createElement('canvas')
  QRCode.toCanvas(
    qrCanvas,
    shareUrl,
    { width: qrSize, margin: 1, color: { dark: '#000000', light: '#ffffff' } },
    (err: Error | null | undefined) => {
      if (err) {
        console.error('QRCode generation failed', err)
        ctx.fillStyle = '#999999'
        ctx.font = '20px sans-serif'
        ctx.textAlign = 'center'
        ctx.fillText('二维码生成失败', width / 2, qrY + qrSize / 2)
        finalize()
        return
      }
      ctx.drawImage(qrCanvas, qrX, qrY, qrSize, qrSize)
      finalize()
    }
  )
}

function finalize() {
  if (!canvasRef.value) return
  shareImageUrl.value = canvasRef.value.toDataURL('image/png')
  generating.value = false
}

function wrapText(ctx: CanvasRenderingContext2D, text: string, maxWidth: number): string[] {
  const lines: string[] = []
  let current = ''
  for (const ch of text) {
    const test = current + ch
    if (ctx.measureText(test).width > maxWidth && current.length > 0) {
      lines.push(current)
      current = ch
    } else {
      current = test
    }
  }
  if (current) lines.push(current)
  if (lines.length === 0) lines.push(text)
  return lines.slice(0, 3)
}

function onCopyLink() {
  navigator.clipboard.writeText(shareUrl).then(() => {
    showToast('链接已复制')
  }).catch(() => {
    showToast('复制失败')
  })
  emit('update:visible', false)
}

function onSaveImage() {
  if (!shareImageUrl.value) return
  const link = document.createElement('a')
  link.download = `${props.apartmentName}.png`
  link.href = shareImageUrl.value
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
}

function onClose() {
  emit('update:visible', false)
}

watch(() => props.visible, (v) => {
  if (v) {
    generating.value = true
    shareImageUrl.value = ''
    nextTick(() => {
      buildShareImage()
    })
  }
})
</script>

<template>
  <van-popup
    :show="visible"
    position="bottom"
    round
    closeable
    @close="onClose"
    @click-close-icon="onClose"
    class="share-popup"
  >
    <div class="share-content">
      <div class="share-title">分享房源</div>

      <div class="share-image-wrapper">
        <canvas
          ref="canvasRef"
          class="share-canvas"
        />
        <img
          v-if="shareImageUrl"
          :src="shareImageUrl"
          :alt="apartmentName"
          class="share-preview"
        />
        <div v-if="generating" class="share-loading">
          <van-loading size="24px" />
          <span class="text-sm text-gray-400 mt-2">生成中...</span>
        </div>
      </div>

      <div class="share-actions">
        <van-button type="primary" block round @click="onSaveImage">
          保存图片
        </van-button>
        <van-button plain type="primary" block round @click="onCopyLink">
          复制链接
        </van-button>
      </div>
    </div>
  </van-popup>
</template>

<style scoped lang="scss">
.share-popup {
  :deep(.van-popup__close-icon) {
    top: 12px;
    right: 12px;
  }
}

.share-content {
  padding: 24px 16px 32px;
}

.share-title {
  text-align: center;
  font-size: 16px;
  font-weight: 600;
  color: #333;
  margin-bottom: 16px;
}

.share-image-wrapper {
  position: relative;
  width: 260px;
  height: 364px;
  margin: 0 auto 20px;
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 4px 12px rgba(0, 0, 0, .08);
  background: #f7f8fa;
}

.share-canvas {
  display: none;
}

.share-preview {
  width: 100%;
  height: 100%;
  object-fit: contain;
}

.share-loading {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}

.share-actions {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 0 16px;
}
</style>
