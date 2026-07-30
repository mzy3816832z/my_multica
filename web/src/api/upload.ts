import request from '@/utils/request'

export interface UploadResult {
  url: string
  path: string
}

export function uploadImage(file: File): Promise<UploadResult> {
  const formData = new FormData()
  formData.append('file', file)
  return request.post('/uploads/image/', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  })
}
