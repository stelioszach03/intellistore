import React, { useState } from 'react'
import { Link } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  PlusIcon,
  FolderIcon,
  MagnifyingGlassIcon,
  TrashIcon,
  EyeIcon,
} from '@heroicons/react/24/outline'
import apiService from '../services/api'
import LoadingSpinner from '../components/LoadingSpinner'
import { formatBytes, formatDate } from '../utils/date'
import toast from 'react-hot-toast'

export default function BucketsPage() {
  const [searchQuery, setSearchQuery] = useState('')
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [newBucketName, setNewBucketName] = useState('')
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null)

  const queryClient = useQueryClient()

  const { data: buckets, isLoading } = useQuery({
    queryKey: ['buckets'],
    queryFn: apiService.getBuckets,
  })

  const createBucketMutation = useMutation({
    mutationFn: apiService.createBucket,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['buckets'] })
      setShowCreateModal(false)
      setNewBucketName('')
      toast.success('Bucket created successfully!')
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.message || 'Failed to create bucket')
    },
  })

  const deleteBucketMutation = useMutation({
    mutationFn: apiService.deleteBucket,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['buckets'] })
      setDeleteConfirm(null)
      toast.success('Bucket deleted successfully!')
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.message || 'Failed to delete bucket')
    },
  })

  const filteredBuckets = buckets?.filter(bucket =>
    bucket.name.toLowerCase().includes(searchQuery.toLowerCase())
  ) || []

  const handleCreateBucket = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!newBucketName.trim()) return

    // Validate bucket name
    const bucketNameRegex = /^[a-z0-9][a-z0-9-]*[a-z0-9]$/
    if (!bucketNameRegex.test(newBucketName)) {
      toast.error('Bucket name must contain only lowercase letters, numbers, and hyphens')
      return
    }

    await createBucketMutation.mutateAsync(newBucketName.trim())
  }

  const handleDeleteBucket = async (bucketName: string) => {
    await deleteBucketMutation.mutateAsync(bucketName)
  }

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
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Buckets</h1>
          <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
            Manage your storage buckets
          </p>
        </div>
        <motion.button
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
          onClick={() => setShowCreateModal(true)}
          className="btn-primary"
        >
          <PlusIcon className="h-5 w-5 mr-2" />
          Create Bucket
        </motion.button>
      </div>

      {/* Search */}
      <div className="relative">
        <MagnifyingGlassIcon className="absolute left-3 top-1/2 transform -translate-y-1/2 h-5 w-5 text-gray-400" />
        <input
          type="text"
          placeholder="Search buckets..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="input pl-10"
        />
      </div>

      {/* Buckets Grid */}
      {filteredBuckets.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredBuckets.map((bucket, index) => (
            <motion.div
              key={bucket.name}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.1 }}
              className="card p-6 hover:shadow-lg transition-shadow"
            >
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center">
                  <div className="p-2 bg-primary-100 dark:bg-primary-900 rounded-lg">
                    <FolderIcon className="h-6 w-6 text-primary-600 dark:text-primary-400" />
                  </div>
                  <div className="ml-3">
                    <h3 className="text-lg font-medium text-gray-900 dark:text-white">
                      {bucket.name}
                    </h3>
                    <p className="text-sm text-gray-500 dark:text-gray-400">
                      {bucket.objectCount} objects
                    </p>
                  </div>
                </div>
                <div className="flex space-x-2">
                  <Link
                    to={`/buckets/${bucket.name}/objects`}
                    className="p-2 text-gray-400 hover:text-gray-500 dark:hover:text-gray-300"
                    title="View objects"
                  >
                    <EyeIcon className="h-5 w-5" />
                  </Link>
                  <button
                    onClick={() => setDeleteConfirm(bucket.name)}
                    className="p-2 text-gray-400 hover:text-red-500"
                    title="Delete bucket"
                  >
                    <TrashIcon className="h-5 w-5" />
                  </button>
                </div>
              </div>

              <div className="space-y-3">
                <div className="flex justify-between text-sm">
                  <span className="text-gray-500 dark:text-gray-400">Total Size</span>
                  <span className="font-medium text-gray-900 dark:text-white">
                    {formatBytes(bucket.totalSize)}
                  </span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-gray-500 dark:text-gray-400">Hot Objects</span>
                  <span className="badge-hot">{bucket.hotCount}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-gray-500 dark:text-gray-400">Cold Objects</span>
                  <span className="badge-cold">{bucket.coldCount}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-gray-500 dark:text-gray-400">Created</span>
                  <span className="text-gray-900 dark:text-white">
                    {formatDate(bucket.createdAt)}
                  </span>
                </div>
              </div>

              <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
                <Link
                  to={`/buckets/${bucket.name}/objects`}
                  className="btn-outline w-full"
                >
                  View Objects
                </Link>
              </div>
            </motion.div>
          ))}
        </div>
      ) : (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="text-center py-12"
        >
          <FolderIcon className="h-12 w-12 mx-auto text-gray-300 dark:text-gray-600 mb-4" />
          <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
            {searchQuery ? 'No buckets found' : 'No buckets yet'}
          </h3>
          <p className="text-gray-500 dark:text-gray-400 mb-6">
            {searchQuery
              ? 'Try adjusting your search query'
              : 'Get started by creating your first bucket'}
          </p>
          {!searchQuery && (
            <motion.button
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              onClick={() => setShowCreateModal(true)}
              className="btn-primary"
            >
              <PlusIcon className="h-5 w-5 mr-2" />
              Create Your First Bucket
            </motion.button>
          )}
        </motion.div>
      )}

      {/* Create Bucket Modal */}
      <AnimatePresence>
        {showCreateModal && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black bg-opacity-50"
            onClick={() => setShowCreateModal(false)}
          >
            <motion.div
              initial={{ scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.95, opacity: 0 }}
              className="bg-white dark:bg-gray-800 rounded-lg shadow-xl p-6 w-full max-w-md"
              onClick={(e) => e.stopPropagation()}
            >
              <h2 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
                Create New Bucket
              </h2>
              <form onSubmit={handleCreateBucket}>
                <div className="mb-4">
                  <label className="label">Bucket Name</label>
                  <input
                    type="text"
                    value={newBucketName}
                    onChange={(e) => setNewBucketName(e.target.value)}
                    className="input"
                    placeholder="my-bucket-name"
                    required
                    pattern="^[a-z0-9][a-z0-9-]*[a-z0-9]$"
                    title="Bucket name must contain only lowercase letters, numbers, and hyphens"
                  />
                  <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                    Only lowercase letters, numbers, and hyphens allowed
                  </p>
                </div>
                <div className="flex space-x-3">
                  <button
                    type="button"
                    onClick={() => setShowCreateModal(false)}
                    className="btn-outline flex-1"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={createBucketMutation.isPending || !newBucketName.trim()}
                    className="btn-primary flex-1"
                  >
                    {createBucketMutation.isPending ? (
                      <LoadingSpinner size="sm" className="text-white" />
                    ) : (
                      'Create'
                    )}
                  </button>
                </div>
              </form>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Delete Confirmation Modal */}
      <AnimatePresence>
        {deleteConfirm && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black bg-opacity-50"
            onClick={() => setDeleteConfirm(null)}
          >
            <motion.div
              initial={{ scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.95, opacity: 0 }}
              className="bg-white dark:bg-gray-800 rounded-lg shadow-xl p-6 w-full max-w-md"
              onClick={(e) => e.stopPropagation()}
            >
              <h2 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
                Delete Bucket
              </h2>
              <p className="text-gray-600 dark:text-gray-400 mb-6">
                Are you sure you want to delete the bucket "{deleteConfirm}"? This action
                cannot be undone and will delete all objects in the bucket.
              </p>
              <div className="flex space-x-3">
                <button
                  onClick={() => setDeleteConfirm(null)}
                  className="btn-outline flex-1"
                >
                  Cancel
                </button>
                <button
                  onClick={() => handleDeleteBucket(deleteConfirm)}
                  disabled={deleteBucketMutation.isPending}
                  className="btn-danger flex-1"
                >
                  {deleteBucketMutation.isPending ? (
                    <LoadingSpinner size="sm" className="text-white" />
                  ) : (
                    'Delete'
                  )}
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}