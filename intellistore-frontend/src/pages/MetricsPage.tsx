import React from 'react'
import { motion } from 'framer-motion'
import { useQuery } from '@tanstack/react-query'
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  PieChart,
  Pie,
  Cell,
  BarChart,
  Bar,
} from 'recharts'
import apiService from '../services/api'
import LoadingSpinner from '../components/LoadingSpinner'
import { formatBytes } from '../utils/date'

export default function MetricsPage() {
  const { data: metrics, isLoading } = useQuery({
    queryKey: ['metrics'],
    queryFn: apiService.getMetrics,
    refetchInterval: 30000, // Refresh every 30 seconds
  })

  const { data: alerts } = useQuery({
    queryKey: ['alerts'],
    queryFn: apiService.getAlerts,
    refetchInterval: 10000, // Refresh every 10 seconds
  })

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <LoadingSpinner size="lg" />
      </div>
    )
  }

  if (!metrics) {
    return (
      <div className="text-center py-12">
        <p className="text-gray-500 dark:text-gray-400">No metrics data available</p>
      </div>
    )
  }

  // Prepare chart data
  const storageData = [
    { name: 'SSD Used', value: metrics.storageUtilization.ssdUsed, color: '#3b82f6' },
    { name: 'HDD Used', value: metrics.storageUtilization.hddUsed, color: '#6b7280' },
    {
      name: 'Available',
      value: metrics.storageUtilization.totalCapacity - metrics.storageUtilization.usedCapacity,
      color: '#e5e7eb',
    },
  ]

  const nodeUtilizationData = metrics.storageUtilization.nodeUtilization.map(node => ({
    name: node.nodeId,
    utilization: node.utilizationPercent,
    tier: node.tier,
  }))

  // Mock time series data for ML tiering
  const timeSeriesData = Array.from({ length: 24 }, (_, i) => ({
    hour: `${i}:00`,
    predictions: Math.floor(Math.random() * 50) + 10,
    migrations: Math.floor(Math.random() * 20) + 5,
  }))

  const activeAlerts = alerts?.filter(alert => alert.status === 'firing') || []

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Metrics Dashboard</h1>
        <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
          Real-time monitoring of your IntelliStore cluster
        </p>
      </div>

      {/* Cluster Health */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="card p-6"
      >
        <h2 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
          Cluster Health
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
          <div className="text-center">
            <div className="text-3xl font-bold text-primary-600 dark:text-primary-400">
              {metrics.clusterHealth.healthyNodes}/{metrics.clusterHealth.totalNodes}
            </div>
            <p className="text-sm text-gray-500 dark:text-gray-400">Healthy Nodes</p>
          </div>
          <div className="text-center">
            <div className="text-3xl font-bold text-secondary-600 dark:text-secondary-400">
              {metrics.clusterHealth.raftLeader}
            </div>
            <p className="text-sm text-gray-500 dark:text-gray-400">Raft Leader</p>
          </div>
          <div className="text-center">
            <div className="text-3xl font-bold text-accent-600 dark:text-accent-400">
              {metrics.clusterHealth.avgCommitLatency.toFixed(1)}ms
            </div>
            <p className="text-sm text-gray-500 dark:text-gray-400">Avg Commit Latency</p>
          </div>
          <div className="text-center">
            <div
              className={`text-3xl font-bold ${
                metrics.clusterHealth.healthyNodes === metrics.clusterHealth.totalNodes
                  ? 'text-green-600'
                  : 'text-red-600'
              }`}
            >
              {metrics.clusterHealth.healthyNodes === metrics.clusterHealth.totalNodes
                ? '✓'
                : '⚠'}
            </div>
            <p className="text-sm text-gray-500 dark:text-gray-400">Status</p>
          </div>
        </div>
      </motion.div>

      {/* Storage Utilization */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="card p-6"
        >
          <h2 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
            Storage Distribution
          </h2>
          <ResponsiveContainer width="100%" height={300}>
            <PieChart>
              <Pie
                data={storageData}
                cx="50%"
                cy="50%"
                innerRadius={60}
                outerRadius={120}
                paddingAngle={5}
                dataKey="value"
                label={({ name, value }) => `${name}: ${formatBytes(value)}`}
              >
                {storageData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} />
                ))}
              </Pie>
              <Tooltip formatter={(value: any) => formatBytes(value)} />
            </PieChart>
          </ResponsiveContainer>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="card p-6"
        >
          <h2 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
            Node Utilization
          </h2>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={nodeUtilizationData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="name" />
              <YAxis />
              <Tooltip formatter={(value: any) => `${value}%`} />
              <Bar
                dataKey="utilization"
                fill={(entry: any) => (entry.tier === 'ssd' ? '#3b82f6' : '#6b7280')}
              />
            </BarChart>
          </ResponsiveContainer>
        </motion.div>
      </div>

      {/* ML Tiering */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.3 }}
        className="card p-6"
      >
        <h2 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
          ML Tiering Activity (Last 24 Hours)
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
          <div className="text-center">
            <div className="text-2xl font-bold text-primary-600 dark:text-primary-400">
              {metrics.mlTiering.totalMigrations}
            </div>
            <p className="text-sm text-gray-500 dark:text-gray-400">Total Migrations</p>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-secondary-600 dark:text-secondary-400">
              {metrics.mlTiering.successfulMigrations}
            </div>
            <p className="text-sm text-gray-500 dark:text-gray-400">Successful</p>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-accent-600 dark:text-accent-400">
              {metrics.mlTiering.migrationLatency.toFixed(1)}s
            </div>
            <p className="text-sm text-gray-500 dark:text-gray-400">Avg Latency</p>
          </div>
        </div>
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={timeSeriesData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="hour" />
            <YAxis />
            <Tooltip />
            <Line
              type="monotone"
              dataKey="predictions"
              stroke="#3b82f6"
              strokeWidth={2}
              name="Hot Predictions"
            />
            <Line
              type="monotone"
              dataKey="migrations"
              stroke="#10b981"
              strokeWidth={2}
              name="Migrations"
            />
          </LineChart>
        </ResponsiveContainer>
      </motion.div>

      {/* Active Alerts */}
      {activeAlerts.length > 0 && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4 }}
          className="card"
        >
          <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
            <h2 className="text-lg font-medium text-gray-900 dark:text-white">
              Active Alerts ({activeAlerts.length})
            </h2>
          </div>
          <div className="overflow-hidden">
            <table className="table">
              <thead className="table-header">
                <tr>
                  <th className="table-header-cell">Alert</th>
                  <th className="table-header-cell">Severity</th>
                  <th className="table-header-cell">Description</th>
                  <th className="table-header-cell">Fired At</th>
                  <th className="table-header-cell">Actions</th>
                </tr>
              </thead>
              <tbody className="table-body">
                {activeAlerts.map((alert) => (
                  <tr key={alert.id}>
                    <td className="table-cell font-medium">{alert.name}</td>
                    <td className="table-cell">
                      <span
                        className={`badge ${
                          alert.severity === 'critical'
                            ? 'badge-error'
                            : alert.severity === 'warning'
                            ? 'badge-warning'
                            : 'badge-success'
                        }`}
                      >
                        {alert.severity}
                      </span>
                    </td>
                    <td className="table-cell text-gray-600 dark:text-gray-400">
                      {alert.description}
                    </td>
                    <td className="table-cell text-gray-500 dark:text-gray-400">
                      {new Date(alert.firedAt).toLocaleString()}
                    </td>
                    <td className="table-cell">
                      <div className="flex space-x-2">
                        <button
                          onClick={() => apiService.acknowledgeAlert(alert.id)}
                          className="text-sm text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300"
                        >
                          Acknowledge
                        </button>
                        <button
                          onClick={() => apiService.silenceAlert(alert.id, 3600)}
                          className="text-sm text-gray-600 hover:text-gray-800 dark:text-gray-400 dark:hover:text-gray-300"
                        >
                          Silence 1h
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </motion.div>
      )}
    </div>
  )
}