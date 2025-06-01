import { Bucket, StorageObject, MetricsData, SystemStatus } from '../types'

// Mock data for development and testing
export const mockBuckets: Bucket[] = [
  {
    name: 'user-uploads',
    createdAt: '2024-01-15T10:30:00Z',
    updatedAt: '2024-05-20T15:30:00Z',
    objectCount: 1247,
    totalSize: 2847392847,
    hotCount: 847,
    coldCount: 400,
    permissions: [
      { username: 'admin', permission: 'admin' },
      { username: 'user', permission: 'write' }
    ]
  },
  {
    name: 'backup-data',
    createdAt: '2024-01-10T08:15:00Z',
    updatedAt: '2024-05-19T08:15:00Z',
    objectCount: 892,
    totalSize: 15847392847,
    hotCount: 92,
    coldCount: 800,
    permissions: [
      { username: 'admin', permission: 'admin' }
    ]
  },
  {
    name: 'media-assets',
    createdAt: '2024-02-01T14:20:00Z',
    updatedAt: '2024-05-20T14:20:00Z',
    objectCount: 3456,
    totalSize: 8947392847,
    hotCount: 2456,
    coldCount: 1000,
    permissions: [
      { username: 'admin', permission: 'admin' },
      { username: 'user', permission: 'write' },
      { username: 'guest', permission: 'read' }
    ]
  },
  {
    name: 'logs-archive',
    createdAt: '2024-01-05T09:45:00Z',
    updatedAt: '2024-05-18T09:45:00Z',
    objectCount: 15678,
    totalSize: 4847392847,
    hotCount: 678,
    coldCount: 15000,
    permissions: [
      { username: 'admin', permission: 'admin' }
    ]
  }
]

export const mockObjects: StorageObject[] = [
  {
    key: 'documents/report-2024.pdf',
    bucketName: 'user-uploads',
    size: 2847392,
    lastModified: '2024-05-15T10:30:00Z',
    lastAccessed: '2024-05-20T10:30:00Z',
    createdAt: '2024-05-15T10:30:00Z',
    etag: 'abc123def456',
    tier: 'hot',
    contentType: 'application/pdf',
    metadata: {
      'user-id': '12345',
      'department': 'finance'
    },
    shards: [
      {
        id: 'shard-1',
        nodeId: 'node-1',
        path: '/data/shard-1',
        size: 2847392,
        checksum: 'abc123'
      }
    ]
  },
  {
    key: 'images/logo.png',
    bucketName: 'media-assets',
    size: 847392,
    lastModified: '2024-05-20T14:15:00Z',
    lastAccessed: '2024-05-20T14:15:00Z',
    createdAt: '2024-05-20T14:15:00Z',
    etag: 'def456ghi789',
    tier: 'hot',
    contentType: 'image/png',
    metadata: {
      'category': 'branding',
      'version': '2.1'
    },
    shards: [
      {
        id: 'shard-2',
        nodeId: 'node-2',
        path: '/data/shard-2',
        size: 847392,
        checksum: 'def456'
      }
    ]
  },
  {
    key: 'backups/database-backup-2024-05-01.sql',
    bucketName: 'backup-data',
    size: 15847392,
    lastModified: '2024-05-01T02:00:00Z',
    lastAccessed: '2024-05-01T02:00:00Z',
    createdAt: '2024-05-01T02:00:00Z',
    etag: 'ghi789jkl012',
    tier: 'cold',
    contentType: 'application/sql',
    metadata: {
      'backup-type': 'full',
      'retention': '7-years'
    },
    shards: [
      {
        id: 'shard-3',
        nodeId: 'node-3',
        path: '/data/shard-3',
        size: 15847392,
        checksum: 'ghi789'
      }
    ]
  }
]

export const mockMetrics: MetricsData = {
  clusterHealth: {
    totalNodes: 3,
    healthyNodes: 3,
    raftLeader: 'node-1',
    avgCommitLatency: 12.5
  },
  storageUtilization: {
    totalCapacity: 1000000000000, // 1TB
    usedCapacity: 320000000000,   // 320GB
    ssdUsed: 120000000000,        // 120GB
    hddUsed: 200000000000,        // 200GB
    nodeUtilization: [
      {
        nodeId: 'node-1',
        tier: 'ssd',
        totalCapacity: 500000000000,
        usedCapacity: 120000000000,
        utilizationPercent: 24
      },
      {
        nodeId: 'node-2',
        tier: 'hdd',
        totalCapacity: 300000000000,
        usedCapacity: 100000000000,
        utilizationPercent: 33
      },
      {
        nodeId: 'node-3',
        tier: 'hdd',
        totalCapacity: 200000000000,
        usedCapacity: 100000000000,
        utilizationPercent: 50
      }
    ]
  },
  mlTiering: {
    hotPredictionsPerHour: [45, 52, 38, 61, 47, 55, 42, 58, 49, 53, 46, 59],
    migrationLatency: 2.3,
    totalMigrations: 1247,
    successfulMigrations: 1235
  },
  alerts: [
    {
      id: 'alert-1',
      name: 'High Storage Utilization',
      severity: 'warning',
      description: 'Node-3 storage utilization is above 80%',
      firedAt: '2024-05-20T14:30:00Z',
      status: 'firing'
    },
    {
      id: 'alert-2',
      name: 'ML Service Latency',
      severity: 'critical',
      description: 'ML prediction latency is above threshold',
      firedAt: '2024-05-20T15:00:00Z',
      status: 'firing'
    }
  ]
}

export const mockSystemStatus: SystemStatus = {
  status: 'healthy',
  uptime: 86400,
  version: '1.0.0',
  components: {
    api: 'healthy',
    raft: 'healthy',
    storage: 'healthy',
    ml: 'healthy',
    vault: 'healthy',
    kafka: 'healthy'
  }
}

// Helper function to format bytes
export const formatBytes = (bytes: number): string => {
  if (bytes === 0) return '0 Bytes'
  
  const k = 1024
  const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

// Helper function to format numbers
export const formatNumber = (num: number): string => {
  if (num >= 1000000) {
    return (num / 1000000).toFixed(1) + 'M'
  } else if (num >= 1000) {
    return (num / 1000).toFixed(1) + 'K'
  }
  return num.toString()
}