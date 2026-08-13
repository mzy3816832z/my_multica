let loadPromise: Promise<any> | null = null
let currentKey: string | null = null

export function loadAMap(key: string, plugins: string[] = []): Promise<any> {
  if (loadPromise && currentKey === key) {
    return loadPromise
  }

  if ((window as any)._AMapSecurityConfig) {
    ;(window as any)._AMapSecurityConfig.securityJsCode = ''
  }

  currentKey = key

  loadPromise = new Promise((resolve, reject) => {
    if ((window as any).AMap && (window as any).AMap.Map) {
      resolve((window as any).AMap)
      return
    }

    const callbackName = '_amap_init_' + Date.now()
    ;(window as any)[callbackName] = () => {
      delete (window as any)[callbackName]
      resolve((window as any).AMap)
    }

    const pluginStr = plugins.length > 0 ? '&plugin=' + plugins.join(',') : ''
    const script = document.createElement('script')
    script.src = `https://webapi.amap.com/maps?v=2.0&key=${encodeURIComponent(key)}${pluginStr}&callback=${callbackName}`
    script.onerror = () => {
      delete (window as any)[callbackName]
      loadPromise = null
      reject(new Error('AMap script load failed'))
    }
    document.head.appendChild(script)
  })

  return loadPromise
}
