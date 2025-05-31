import React, { useState } from 'react'
import { motion } from 'framer-motion'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useAuth } from '../hooks/useAuth'
import apiService from '../services/api'
import LoadingSpinner from '../components/LoadingSpinner'
import toast from 'react-hot-toast'

export default function SettingsPage() {
  const { user } = useAuth()
  const [activeTab, setActiveTab] = useState('profile')
  const [selectedBucket, setSelectedBucket] = useState<string | null>(null)
  const queryClient = useQueryClient()

  const { data: buckets } = useQuery({
    queryKey: ['buckets'],
    queryFn: apiService.getBuckets,
  })

  const { data: bucketPermissions, isLoading: permissionsLoading } = useQuery({
    queryKey: ['bucketPermissions', selectedBucket],
    queryFn: () => apiService.getBucketPermissions(selectedBucket!),
    enabled: !!selectedBucket,
  })

  const updatePermissionsMutation = useMutation({
    mutationFn: ({ bucketName, permissions }: { bucketName: string; permissions: any }) =>
      apiService.updateBucketPermissions(bucketName, permissions),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['bucketPermissions', selectedBucket] })
      toast.success('Permissions updated successfully!')
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.message || 'Failed to update permissions')
    },
  })

  const tabs = [
    { id: 'profile', name: 'Profile', icon: '👤' },
    { id: 'buckets', name: 'Bucket Permissions', icon: '🔒' },
    { id: 'system', name: 'System', icon: '⚙️' },
  ]

  const handleUpdatePermissions = async (permissions: any) => {
    if (!selectedBucket) return
    await updatePermissionsMutation.mutateAsync({ bucketName: selectedBucket, permissions })
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Settings</h1>
        <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
          Manage your account and system preferences
        </p>
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200 dark:border-gray-700">
        <nav className="-mb-px flex space-x-8">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`py-2 px-1 border-b-2 font-medium text-sm ${
                activeTab === tab.id
                  ? 'border-primary-500 text-primary-600 dark:text-primary-400'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300 dark:text-gray-400 dark:hover:text-gray-300'
              }`}
            >
              <span className="mr-2">{tab.icon}</span>
              {tab.name}
            </button>
          ))}
        </nav>
      </div>

      {/* Tab Content */}
      <motion.div
        key={activeTab}
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3 }}
      >
        {activeTab === 'profile' && (
          <div className="card p-6">
            <h2 className="text-lg font-medium text-gray-900 dark:text-white mb-6">
              Profile Information
            </h2>
            <div className="space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <label className="label">Username</label>
                  <input
                    type="text"
                    value={user?.username || ''}
                    disabled
                    className="input bg-gray-50 dark:bg-gray-700"
                  />
                </div>
                <div>
                  <label className="label">Email</label>
                  <input
                    type="email"
                    value={user?.email || ''}
                    disabled
                    className="input bg-gray-50 dark:bg-gray-700"
                  />
                </div>
                <div>
                  <label className="label">Role</label>
                  <input
                    type="text"
                    value={user?.role || ''}
                    disabled
                    className="input bg-gray-50 dark:bg-gray-700 capitalize"
                  />
                </div>
                <div>
                  <label className="label">Member Since</label>
                  <input
                    type="text"
                    value={user?.createdAt ? new Date(user.createdAt).toLocaleDateString() : ''}
                    disabled
                    className="input bg-gray-50 dark:bg-gray-700"
                  />
                </div>
              </div>
              
              <div className="pt-6 border-t border-gray-200 dark:border-gray-700">
                <h3 className="text-md font-medium text-gray-900 dark:text-white mb-4">
                  Change Password
                </h3>
                <div className="space-y-4">
                  <div>
                    <label className="label">Current Password</label>
                    <input type="password" className="input" placeholder="Enter current password" />
                  </div>
                  <div>
                    <label className="label">New Password</label>
                    <input type="password" className="input" placeholder="Enter new password" />
                  </div>
                  <div>
                    <label className="label">Confirm New Password</label>
                    <input type="password" className="input" placeholder="Confirm new password" />
                  </div>
                  <button className="btn-primary">Update Password</button>
                </div>
              </div>
            </div>
          </div>
        )}

        {activeTab === 'buckets' && (
          <div className="space-y-6">
            {/* Bucket Selection */}
            <div className="card p-6">
              <h2 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
                Bucket Permissions
              </h2>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {buckets?.map((bucket) => (
                  <button
                    key={bucket.name}
                    onClick={() => setSelectedBucket(bucket.name)}
                    className={`p-4 rounded-lg border text-left transition-colors ${
                      selectedBucket === bucket.name
                        ? 'border-primary-500 bg-primary-50 dark:bg-primary-900/20'
                        : 'border-gray-200 dark:border-gray-700 hover:border-gray-300 dark:hover:border-gray-600'
                    }`}
                  >
                    <div className="font-medium text-gray-900 dark:text-white">
                      {bucket.name}
                    </div>
                    <div className="text-sm text-gray-500 dark:text-gray-400">
                      {bucket.objectCount} objects
                    </div>
                  </button>
                ))}
              </div>
            </div>

            {/* Permissions Management */}
            {selectedBucket && (
              <div className="card p-6">
                <div className="flex items-center justify-between mb-6">
                  <h3 className="text-lg font-medium text-gray-900 dark:text-white">
                    Permissions for "{selectedBucket}"
                  </h3>
                  <button className="btn-primary">Add User</button>
                </div>

                {permissionsLoading ? (
                  <div className="flex justify-center py-8">
                    <LoadingSpinner size="lg" />
                  </div>
                ) : (
                  <div className="overflow-hidden">
                    <table className="table">
                      <thead className="table-header">
                        <tr>
                          <th className="table-header-cell">User</th>
                          <th className="table-header-cell">Permission</th>
                          <th className="table-header-cell">Actions</th>
                        </tr>
                      </thead>
                      <tbody className="table-body">
                        {bucketPermissions?.map((permission: any, index: number) => (
                          <tr key={index}>
                            <td className="table-cell">
                              <div className="flex items-center">
                                <div className="w-8 h-8 bg-gray-300 dark:bg-gray-600 rounded-full flex items-center justify-center mr-3">
                                  <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                                    {permission.username.charAt(0).toUpperCase()}
                                  </span>
                                </div>
                                <span className="font-medium">{permission.username}</span>
                              </div>
                            </td>
                            <td className="table-cell">
                              <select
                                value={permission.permission}
                                onChange={(e) => {
                                  // Handle permission change
                                }}
                                className="input"
                              >
                                <option value="read">Read</option>
                                <option value="write">Write</option>
                                <option value="admin">Admin</option>
                              </select>
                            </td>
                            <td className="table-cell">
                              <button className="text-red-600 hover:text-red-800 dark:text-red-400 dark:hover:text-red-300">
                                Remove
                              </button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {activeTab === 'system' && (
          <div className="space-y-6">
            {/* System Information */}
            <div className="card p-6">
              <h2 className="text-lg font-medium text-gray-900 dark:text-white mb-6">
                System Information
              </h2>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <label className="label">Version</label>
                  <input
                    type="text"
                    value="1.0.0"
                    disabled
                    className="input bg-gray-50 dark:bg-gray-700"
                  />
                </div>
                <div>
                  <label className="label">Build Date</label>
                  <input
                    type="text"
                    value="2024-01-15"
                    disabled
                    className="input bg-gray-50 dark:bg-gray-700"
                  />
                </div>
                <div>
                  <label className="label">API Endpoint</label>
                  <input
                    type="text"
                    value={window.location.origin + '/api'}
                    disabled
                    className="input bg-gray-50 dark:bg-gray-700"
                  />
                </div>
                <div>
                  <label className="label">WebSocket Status</label>
                  <input
                    type="text"
                    value="Connected"
                    disabled
                    className="input bg-gray-50 dark:bg-gray-700"
                  />
                </div>
              </div>
            </div>

            {/* System Settings */}
            <div className="card p-6">
              <h2 className="text-lg font-medium text-gray-900 dark:text-white mb-6">
                System Settings
              </h2>
              <div className="space-y-6">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="text-sm font-medium text-gray-900 dark:text-white">
                      Auto-refresh Metrics
                    </h3>
                    <p className="text-sm text-gray-500 dark:text-gray-400">
                      Automatically refresh dashboard metrics every 30 seconds
                    </p>
                  </div>
                  <label className="relative inline-flex items-center cursor-pointer">
                    <input type="checkbox" className="sr-only peer" defaultChecked />
                    <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-primary-300 dark:peer-focus:ring-primary-800 rounded-full peer dark:bg-gray-700 peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all dark:border-gray-600 peer-checked:bg-primary-600"></div>
                  </label>
                </div>

                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="text-sm font-medium text-gray-900 dark:text-white">
                      Enable Notifications
                    </h3>
                    <p className="text-sm text-gray-500 dark:text-gray-400">
                      Receive real-time notifications for system events
                    </p>
                  </div>
                  <label className="relative inline-flex items-center cursor-pointer">
                    <input type="checkbox" className="sr-only peer" defaultChecked />
                    <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-primary-300 dark:peer-focus:ring-primary-800 rounded-full peer dark:bg-gray-700 peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all dark:border-gray-600 peer-checked:bg-primary-600"></div>
                  </label>
                </div>

                <div>
                  <label className="label">Default Page Size</label>
                  <select className="input">
                    <option value="10">10 items</option>
                    <option value="20" selected>20 items</option>
                    <option value="50">50 items</option>
                    <option value="100">100 items</option>
                  </select>
                </div>

                <div className="pt-4">
                  <button className="btn-primary">Save Settings</button>
                </div>
              </div>
            </div>
          </div>
        )}
      </motion.div>
    </div>
  )
}