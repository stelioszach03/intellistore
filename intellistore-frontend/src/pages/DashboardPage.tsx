import React from 'react'
import { motion } from 'framer-motion'
import { useQuery } from '@tanstack/react-query'
import {
  FolderIcon,
  ServerIcon,
  ChartBarIcon,
  ExclamationTriangleIcon,
} from '@heroicons/react/24/outline'
import apiService from '../services/api'
import LoadingSpinner from '../components/LoadingSpinner'
import { formatBytes } from '../utils/date'

export default function DashboardPage() {
  const { data: buckets, isLoading: bucketsLoading } = useQuery({
    queryKey: ['buckets'],
    queryFn: apiService.getBuckets,
  })

  const { data: metrics, isLoading: metricsLoading } = useQuery({
    queryKey: ['metrics'],
    queryFn: apiService.getMetrics,
    refetchInterval: 30000, // Refresh every 30 seconds
  })

  const { data: systemStatus, isLoading: statusLoading } = useQuery({
    queryKey: ['systemStatus'],
    queryFn: apiService.getSystemStatus,
    refetchInterval: 10000, // Refresh every 10 seconds
  })

  const isLoading = bucketsLoading || metricsLoading || statusLoading

  const stats = [
    {
      name: 'Total Buckets',
      value: buckets?.length || 0,
      icon: FolderIcon,
      color: 'text-primary-600',
      bgColor: 'bg-primary-100 dark:bg-primary-900',
    },
    {
      name: 'Total Objects',
      value: buckets?.reduce((sum, bucket) => sum + bucket.objectCount, 0) || 0,
      icon: ServerIcon,
      color: 'text-secondary-600',
      bgColor: 'bg-secondary-100 dark:bg-secondary-900',
    },
    {
      name: 'Storage Used',
      value: formatBytes(buckets?.reduce((sum, bucket) => sum + bucket.totalSize, 0) || 0),
      icon: ChartBarIcon,
      color: 'text-accent-600',
      bgColor: 'bg-accent-100 dark:bg-accent-900',
    },
    {
      name: 'Active Alerts',
      value: metrics?.alerts?.filter(alert => alert.status === 'firing').length || 0,
      icon: ExclamationTriangleIcon,
      color: 'text-red-600',
      bgColor: 'bg-red-100 dark:bg-red-900',
    },
  ]

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <LoadingSpinner size="lg" />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Dashboard</h1>
        <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
          Overview of your IntelliStore cluster
        </p>
      </div>

      {/* System Status */}
      {systemStatus && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="card p-6"
        >
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-medium text-gray-900 dark:text-white">
                System Status
              </h2>
              <p className="text-sm text-gray-500 dark:text-gray-400">
                Overall health of your cluster
              </p>
            </div>
            <div className="flex items-center space-x-2">
              <div
                className={`w-3 h-3 rounded-full ${
                  systemStatus.status === 'healthy'
                    ? 'bg-green-500'
                    : systemStatus.status === 'degraded'
                    ? 'bg-yellow-500'
                    : 'bg-red-500'
                }`}
              />
              <span className="text-sm font-medium text-gray-900 dark:text-white capitalize">
                {systemStatus.status}
              </span>
            </div>
          </div>

          <div className="mt-6 grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
            {Object.entries(systemStatus.components).map(([component, status]) => (
              <div key={component} className="text-center">
                <div
                  className={`w-8 h-8 mx-auto rounded-full flex items-center justify-center ${
                    status === 'healthy' ? 'bg-green-100 dark:bg-green-900' : 'bg-red-100 dark:bg-red-900'
                  }`}
                >
                  <div
                    className={`w-3 h-3 rounded-full ${
                      status === 'healthy' ? 'bg-green-500' : 'bg-red-500'
                    }`}
                  />
                </div>
                <p className="mt-2 text-xs font-medium text-gray-900 dark:text-white capitalize">
                  {component}
                </p>
              </div>
            ))}
          </div>
        </motion.div>
      )}

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {stats.map((stat, index) => (
          <motion.div
            key={stat.name}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.1 }}
            className="card p-6"
          >
            <div className="flex items-center">
              <div className={`p-3 rounded-lg ${stat.bgColor}`}>
                <stat.icon className={`h-6 w-6 ${stat.color}`} />
              </div>
              <div className="ml-4">
                <p className="text-sm font-medium text-gray-500 dark:text-gray-400">
                  {stat.name}
                </p>
                <p className="text-2xl font-semibold text-gray-900 dark:text-white">
                  {stat.value}
                </p>
              </div>
            </div>
          </motion.div>
        ))}
      </div>

      {/* Recent Buckets */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.4 }}
        className="card"
      >
        <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
          <h2 className="text-lg font-medium text-gray-900 dark:text-white">
            Recent Buckets
          </h2>
        </div>
        <div className="overflow-hidden">
          {buckets && buckets.length > 0 ? (
            <table className="table">
              <thead className="table-header">
                <tr>
                  <th className="table-header-cell">Name</th>
                  <th className="table-header-cell">Objects</th>
                  <th className="table-header-cell">Size</th>
                  <th className="table-header-cell">Hot/Cold</th>
                  <th className="table-header-cell">Created</th>
                </tr>
              </thead>
              <tbody className="table-body">
                {buckets.slice(0, 5).map((bucket) => (
                  <tr key={bucket.name}>
                    <td className="table-cell">
                      <div className="flex items-center">
                        <FolderIcon className="h-5 w-5 text-gray-400 mr-3" />
                        <span className="font-medium">{bucket.name}</span>
                      </div>
                    </td>
                    <td className="table-cell">{bucket.objectCount}</td>
                    <td className="table-cell">{formatBytes(bucket.totalSize)}</td>
                    <td className="table-cell">
                      <div className="flex space-x-2">
                        <span className="badge-hot">{bucket.hotCount} hot</span>
                        <span className="badge-cold">{bucket.coldCount} cold</span>
                      </div>
                    </td>
                    <td className="table-cell text-gray-500 dark:text-gray-400">
                      {new Date(bucket.createdAt).toLocaleDateString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <div className="p-6 text-center text-gray-500 dark:text-gray-400">
              <FolderIcon className="h-12 w-12 mx-auto mb-4 text-gray-300 dark:text-gray-600" />
              <p>No buckets created yet</p>
            </div>
          )}
        </div>
      </motion.div>

      {/* Active Alerts */}
      {metrics?.alerts && metrics.alerts.length > 0 && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.5 }}
          className="card"
        >
          <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
            <h2 className="text-lg font-medium text-gray-900 dark:text-white">
              Active Alerts
            </h2>
          </div>
          <div className="p-6">
            <div className="space-y-3">
              {metrics.alerts
                .filter(alert => alert.status === 'firing')
                .slice(0, 3)
                .map((alert) => (
                  <div
                    key={alert.id}
                    className={`p-3 rounded-lg border ${
                      alert.severity === 'critical'
                        ? 'bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800'
                        : 'bg-yellow-50 dark:bg-yellow-900/20 border-yellow-200 dark:border-yellow-800'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="font-medium text-gray-900 dark:text-white">
                          {alert.name}
                        </p>
                        <p className="text-sm text-gray-600 dark:text-gray-400">
                          {alert.description}
                        </p>
                      </div>
                      <span
                        className={`badge ${
                          alert.severity === 'critical' ? 'badge-error' : 'badge-warning'
                        }`}
                      >
                        {alert.severity}
                      </span>
                    </div>
                  </div>
                ))}
            </div>
          </div>
        </motion.div>
      )}
    </div>
  )
}