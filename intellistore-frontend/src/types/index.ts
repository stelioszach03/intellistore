export interface User {
  id: string
  username: string
  email: string
  role: 'admin' | 'user'
  createdAt: string
}

export interface Bucket {
  name: string
  objectCount: number
  totalSize: number
  hotCount: number
  coldCount: number
  createdAt: string
  updatedAt: string
  permissions: BucketPermission[]
}

export interface BucketPermission {
  username: string
  permission: 'read' | 'write' | 'admin'
}

export interface StorageObject {
  key: string
  bucketName: string
  size: number
  tier: 'hot' | 'cold'
  contentType: string
  etag: string
  createdAt: string
  lastAccessed: string
  lastModified: string
  metadata: Record<string, string>
  shards: ShardInfo[]
}

export interface ShardInfo {
  id: string
  nodeId: string
  path: string
  size: number
  checksum: string
}

export interface UploadProgress {
  objectKey: string
  totalShards: number
  completedShards: number
  failedShards: number
  status: 'pending' | 'uploading' | 'completed' | 'failed'
  error?: string
}

export interface MetricsData {
  clusterHealth: {
    totalNodes: number
    healthyNodes: number
    raftLeader: string
    avgCommitLatency: number
  }
  storageUtilization: {
    totalCapacity: number
    usedCapacity: number
    ssdUsed: number
    hddUsed: number
    nodeUtilization: NodeUtilization[]
  }
  mlTiering: {
    hotPredictionsPerHour: number[]
    migrationLatency: number
    totalMigrations: number
    successfulMigrations: number
  }
  alerts: Alert[]
}

export interface NodeUtilization {
  nodeId: string
  tier: 'ssd' | 'hdd'
  totalCapacity: number
  usedCapacity: number
  utilizationPercent: number
}

export interface Alert {
  id: string
  name: string
  severity: 'critical' | 'warning' | 'info'
  description: string
  firedAt: string
  status: 'firing' | 'resolved'
}

export interface WebSocketMessage {
  type: 'notification' | 'upload_progress' | 'tier_migration' | 'alert'
  data: any
  timestamp: string
}

export interface Notification {
  id: string
  type: 'success' | 'warning' | 'error' | 'info'
  title: string
  message: string
  timestamp: string
  read: boolean
}

export interface APIError {
  message: string
  code: string
  details?: Record<string, any>
}

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  pageSize: number
  hasNext: boolean
  hasPrev: boolean
}

export interface SearchFilters {
  query?: string
  tier?: 'hot' | 'cold'
  dateFrom?: string
  dateTo?: string
  sortBy?: string
  sortOrder?: 'asc' | 'desc'
}

export interface TierMigrationRequest {
  bucketName: string
  objectKey: string
  targetTier: 'hot' | 'cold'
  reason: string
}

export interface SystemStatus {
  version: string
  uptime: number
  status: 'healthy' | 'degraded' | 'unhealthy'
  components: {
    api: 'healthy' | 'unhealthy'
    raft: 'healthy' | 'unhealthy'
    storage: 'healthy' | 'unhealthy'
    ml: 'healthy' | 'unhealthy'
    vault: 'healthy' | 'unhealthy'
    kafka: 'healthy' | 'unhealthy'
  }
}