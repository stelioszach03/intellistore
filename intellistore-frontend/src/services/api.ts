import axios, { AxiosInstance, AxiosResponse } from 'axios'
import toast from 'react-hot-toast'
import { 
  User, 
  Bucket, 
  StorageObject, 
  MetricsData, 
  PaginatedResponse, 
  SearchFilters,
  TierMigrationRequest,
  SystemStatus,
  APIError
} from '../types'

class APIService {
  private client: AxiosInstance
  private token: string | null = null

  constructor() {
    this.client = axios.create({
      baseURL: '/api',
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json',
      },
    })

    // Initialize token from localStorage
    this.token = this.getStoredToken()

    // Request interceptor to add auth token
    this.client.interceptors.request.use(
      (config) => {
        if (this.token) {
          config.headers.Authorization = `Bearer ${this.token}`
        }
        return config
      },
      (error) => Promise.reject(error)
    )

    // Response interceptor for error handling
    this.client.interceptors.response.use(
      (response) => response,
      (error) => {
        if (error.response?.status === 401) {
          this.clearToken()
          window.location.href = '/login'
        } else if (error.response?.status >= 500) {
          toast.error('Server error occurred. Please try again.')
        } else if (error.response?.data?.message) {
          toast.error(error.response.data.message)
        }
        return Promise.reject(error)
      }
    )
  }

  setToken(token: string) {
    this.token = token
    localStorage.setItem('intellistore_token', token)
  }

  clearToken() {
    this.token = null
    localStorage.removeItem('intellistore_token')
  }

  getStoredToken(): string | null {
    return localStorage.getItem('intellistore_token')
  }

  // Auth endpoints
  async login(username: string, password: string): Promise<{ user: User; token: string }> {
    const response = await this.client.post('/auth/login', { username, password })
    const token = response.data.access_token
    
    // Set token temporarily to get user info
    this.setToken(token)
    
    // Get user info
    const userResponse = await this.client.get('/auth/me')
    
    return {
      token,
      user: userResponse.data
    }
  }

  async logout(): Promise<void> {
    try {
      await this.client.post('/auth/logout')
    } finally {
      this.clearToken()
    }
  }

  async getCurrentUser(): Promise<User> {
    const response = await this.client.get('/auth/me')
    return response.data
  }

  // Bucket endpoints
  async getBuckets(): Promise<Bucket[]> {
    const response = await this.client.get('/buckets')
    return response.data
  }

  async createBucket(name: string): Promise<Bucket> {
    const response = await this.client.post(`/buckets/${name}`)
    return response.data
  }

  async deleteBucket(name: string): Promise<void> {
    await this.client.delete(`/buckets/${name}`)
  }

  async getBucketPermissions(bucketName: string): Promise<any> {
    const response = await this.client.get(`/buckets/${bucketName}/permissions`)
    return response.data
  }

  async updateBucketPermissions(bucketName: string, permissions: any): Promise<void> {
    await this.client.put(`/buckets/${bucketName}/permissions`, permissions)
  }

  // Object endpoints
  async getObjects(
    bucketName: string, 
    filters?: SearchFilters,
    page = 1,
    pageSize = 20
  ): Promise<PaginatedResponse<StorageObject>> {
    const params = new URLSearchParams({
      page: page.toString(),
      page_size: pageSize.toString(),
      ...filters,
    })
    const response = await this.client.get(`/buckets/${bucketName}/objects?${params}`)
    return response.data
  }

  async getObject(bucketName: string, objectKey: string): Promise<StorageObject> {
    const response = await this.client.get(`/buckets/${bucketName}/objects/${objectKey}`)
    return response.data
  }

  async uploadObject(
    bucketName: string,
    objectKey: string,
    file: File,
    onProgress?: (progress: number) => void
  ): Promise<StorageObject> {
    const formData = new FormData()
    formData.append('file', file)

    const response = await this.client.post(
      `/buckets/${bucketName}/objects/${objectKey}`,
      formData,
      {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
        onUploadProgress: (progressEvent) => {
          if (onProgress && progressEvent.total) {
            const progress = Math.round((progressEvent.loaded * 100) / progressEvent.total)
            onProgress(progress)
          }
        },
      }
    )
    return response.data
  }

  async downloadObject(bucketName: string, objectKey: string): Promise<Blob> {
    const response = await this.client.get(
      `/buckets/${bucketName}/objects/${objectKey}/download`,
      { responseType: 'blob' }
    )
    return response.data
  }

  async deleteObject(bucketName: string, objectKey: string): Promise<void> {
    await this.client.delete(`/buckets/${bucketName}/objects/${objectKey}`)
  }

  async migrateObjectTier(
    bucketName: string,
    objectKey: string,
    targetTier: 'hot' | 'cold'
  ): Promise<void> {
    await this.client.patch(`/buckets/${bucketName}/objects/${objectKey}`, {
      tier: targetTier,
    })
  }

  // Metrics endpoints
  async getMetrics(): Promise<MetricsData> {
    const response = await this.client.get('/metrics/dashboard')
    return response.data
  }

  async getSystemStatus(): Promise<SystemStatus> {
    const response = await this.client.get('/health')
    return response.data
  }

  // Prometheus metrics (for charts)
  async queryPrometheus(query: string, start?: string, end?: string, step?: string): Promise<any> {
    const params = new URLSearchParams({ query })
    if (start) params.append('start', start)
    if (end) params.append('end', end)
    if (step) params.append('step', step)

    const response = await this.client.get(`/metrics/prometheus/query_range?${params}`)
    return response.data
  }

  // Alerts
  async getAlerts(): Promise<any[]> {
    const response = await this.client.get('/metrics/alerts')
    return response.data
  }

  async acknowledgeAlert(alertId: string): Promise<void> {
    await this.client.post(`/metrics/alerts/${alertId}/acknowledge`)
  }

  async silenceAlert(alertId: string, duration: number): Promise<void> {
    await this.client.post(`/metrics/alerts/${alertId}/silence`, { duration })
  }
}

export const apiService = new APIService()

// Initialize token from localStorage
const storedToken = apiService.getStoredToken()
if (storedToken) {
  apiService.setToken(storedToken)
}

export default apiService