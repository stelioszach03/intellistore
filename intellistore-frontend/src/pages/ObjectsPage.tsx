import React, { useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  ArrowLeftIcon,
  CloudArrowUpIcon,
  CloudArrowDownIcon,
  TrashIcon,
  MagnifyingGlassIcon,
  FunnelIcon,
  DocumentIcon,
} from '@heroicons/react/24/outline'
import { useDropzone } from 'react-dropzone'
import apiService from '../services/api'
import LoadingSpinner from '../components/LoadingSpinner'
import { formatBytes, formatDate } from '../utils/date'
import { SearchFilters } from '../types'
import toast from 'react-hot-toast'

export default function ObjectsPage() {
  const { bucketName } = useParams<{ bucketName: string }>()
  const [searchQuery, setSearchQuery] = useState('')
  const [tierFilter, setTierFilter] = useState<'all' | 'hot' | 'cold'>('all')
  const [showUploadModal, setShowUploadModal] = useState(false)
  const [uploadProgress, setUploadProgress] = useState<Record<string, number>>({})
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null)

  const queryClient = useQueryClient()

  const filters: SearchFilters = {
    query: searchQuery || undefined,
    tier: tierFilter === 'all' ? undefined : tierFilter,
  }

  const { data: objectsResponse, isLoading } = useQuery({
    queryKey: ['objects', bucketName, filters],
    queryFn: () => apiService.getObjects(bucketName!, filters),
    enabled: !!bucketName,
  })

  const uploadMutation = useMutation({
    mutationFn: ({ file, objectKey }: { file: File; objectKey: string }) =>
      apiService.uploadObject(bucketName!, objectKey, file, (progress) => {
        setUploadProgress(prev => ({ ...prev, [objectKey]: progress }))
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['objects', bucketName] })
      setShowUploadModal(false)
      setUploadProgress({})
      toast.success('File uploaded successfully!')
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.message || 'Upload failed')
      setUploadProgress({})
    },
  })

  const deleteMutation = useMutation({
    mutationFn: (objectKey: string) => apiService.deleteObject(bucketName!, objectKey),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['objects', bucketName] })
      setDeleteConfirm(null)
      toast.success('Object deleted successfully!')
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.message || 'Delete failed')
    },
  })

  const migrateTierMutation = useMutation({
    mutationFn: ({ objectKey, targetTier }: { objectKey: string; targetTier: 'hot' | 'cold' }) =>
      apiService.migrateObjectTier(bucketName!, objectKey, targetTier),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['objects', bucketName] })
      toast.success('Tier migration initiated!')
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.message || 'Migration failed')
    },
  })

  const onDrop = (acceptedFiles: File[]) => {
    acceptedFiles.forEach(file => {
      const objectKey = file.name
      uploadMutation.mutate({ file, objectKey })
    })
  }

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    multiple: true,
  })

  const handleDownload = async (objectKey: string) => {
    try {
      const blob = await apiService.downloadObject(bucketName!, objectKey)
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = objectKey
      document.body.appendChild(a)
      a.click()
      window.URL.revokeObjectURL(url)
      document.body.removeChild(a)
      toast.success('Download started!')
    } catch (error: any) {
      toast.error(error.response?.data?.message || 'Download failed')
    }
  }

  const handleDelete = async (objectKey: string) => {
    await deleteMutation.mutateAsync(objectKey)
  }

  const handleMigrateTier = async (objectKey: string, targetTier: 'hot' | 'cold') => {
    await migrateTierMutation.mutateAsync({ objectKey, targetTier })
  }

  if (!bucketName) {
    return <div>Invalid bucket name</div>
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <LoadingSpinner size="lg" />
      </div>
    )
  }

  const objects = objectsResponse?.items || []

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <Link
            to="/buckets"
            className="p-2 text-gray-400 hover:text-gray-500 dark:hover:text-gray-300"
          >
            <ArrowLeftIcon className="h-5 w-5" />
          </Link>
          <div>
            <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
              {bucketName}
            </h1>
            <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
              {objectsResponse?.total || 0} objects
            </p>
          </div>
        </div>
        <motion.button
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
          onClick={() => setShowUploadModal(true)}
          className="btn-primary"
        >
          <CloudArrowUpIcon className="h-5 w-5 mr-2" />
          Upload Files
        </motion.button>
      </div>

      {/* Filters */}
      <div className="flex flex-col sm:flex-row space-y-4 sm:space-y-0 sm:space-x-4">
        <div className="relative flex-1">
          <MagnifyingGlassIcon className="absolute left-3 top-1/2 transform -translate-y-1/2 h-5 w-5 text-gray-400" />
          <input
            type="text"
            placeholder="Search objects..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="input pl-10"
          />
        </div>
        <div className="relative">
          <FunnelIcon className="absolute left-3 top-1/2 transform -translate-y-1/2 h-5 w-5 text-gray-400" />
          <select
            value={tierFilter}
            onChange={(e) => setTierFilter(e.target.value as any)}
            className="input pl-10 pr-8"
          >
            <option value="all">All Tiers</option>
            <option value="hot">Hot Tier</option>
            <option value="cold">Cold Tier</option>
          </select>
        </div>
      </div>

      {/* Objects Table */}
      {objects.length > 0 ? (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="card overflow-hidden"
        >
          <table className="table">
            <thead className="table-header">
              <tr>
                <th className="table-header-cell">Name</th>
                <th className="table-header-cell">Size</th>
                <th className="table-header-cell">Tier</th>
                <th className="table-header-cell">Last Modified</th>
                <th className="table-header-cell">Actions</th>
              </tr>
            </thead>
            <tbody className="table-body">
              {objects.map((object) => (
                <tr key={object.key}>
                  <td className="table-cell">
                    <div className="flex items-center">
                      <DocumentIcon className="h-5 w-5 text-gray-400 mr-3" />
                      <div>
                        <span className="font-medium">{object.key}</span>
                        <p className="text-xs text-gray-500 dark:text-gray-400">
                          {object.contentType}
                        </p>
                      </div>
                    </div>
                  </td>
                  <td className="table-cell">{formatBytes(object.size)}</td>
                  <td className="table-cell">
                    <span className={object.tier === 'hot' ? 'badge-hot' : 'badge-cold'}>
                      {object.tier}
                    </span>
                  </td>
                  <td className="table-cell text-gray-500 dark:text-gray-400">
                    {formatDate(object.lastModified)}
                  </td>
                  <td className="table-cell">
                    <div className="flex space-x-2">
                      <button
                        onClick={() => handleDownload(object.key)}
                        className="p-1 text-gray-400 hover:text-blue-500"
                        title="Download"
                      >
                        <CloudArrowDownIcon className="h-4 w-4" />
                      </button>
                      <button
                        onClick={() => handleMigrateTier(
                          object.key,
                          object.tier === 'hot' ? 'cold' : 'hot'
                        )}
                        className="p-1 text-gray-400 hover:text-yellow-500"
                        title={`Move to ${object.tier === 'hot' ? 'cold' : 'hot'} tier`}
                        disabled={migrateTierMutation.isPending}
                      >
                        {migrateTierMutation.isPending ? (
                          <LoadingSpinner size="sm" />
                        ) : (
                          <span className="text-xs">
                            {object.tier === 'hot' ? '❄️' : '🔥'}
                          </span>
                        )}
                      </button>
                      <button
                        onClick={() => setDeleteConfirm(object.key)}
                        className="p-1 text-gray-400 hover:text-red-500"
                        title="Delete"
                      >
                        <TrashIcon className="h-4 w-4" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </motion.div>
      ) : (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="text-center py-12"
        >
          <DocumentIcon className="h-12 w-12 mx-auto text-gray-300 dark:text-gray-600 mb-4" />
          <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-2">
            {searchQuery || tierFilter !== 'all' ? 'No objects found' : 'No objects yet'}
          </h3>
          <p className="text-gray-500 dark:text-gray-400 mb-6">
            {searchQuery || tierFilter !== 'all'
              ? 'Try adjusting your search or filters'
              : 'Upload your first file to get started'}
          </p>
          {!searchQuery && tierFilter === 'all' && (
            <motion.button
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              onClick={() => setShowUploadModal(true)}
              className="btn-primary"
            >
              <CloudArrowUpIcon className="h-5 w-5 mr-2" />
              Upload Your First File
            </motion.button>
          )}
        </motion.div>
      )}

      {/* Upload Modal */}
      <AnimatePresence>
        {showUploadModal && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black bg-opacity-50"
            onClick={() => setShowUploadModal(false)}
          >
            <motion.div
              initial={{ scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.95, opacity: 0 }}
              className="bg-white dark:bg-gray-800 rounded-lg shadow-xl p-6 w-full max-w-lg"
              onClick={(e) => e.stopPropagation()}
            >
              <h2 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
                Upload Files
              </h2>
              
              <div
                {...getRootProps()}
                className={`border-2 border-dashed rounded-lg p-8 text-center cursor-pointer transition-colors ${
                  isDragActive
                    ? 'border-primary-500 bg-primary-50 dark:bg-primary-900/20'
                    : 'border-gray-300 dark:border-gray-600 hover:border-primary-400'
                }`}
              >
                <input {...getInputProps()} />
                <CloudArrowUpIcon className="h-12 w-12 mx-auto text-gray-400 mb-4" />
                {isDragActive ? (
                  <p className="text-primary-600 dark:text-primary-400">
                    Drop the files here...
                  </p>
                ) : (
                  <div>
                    <p className="text-gray-600 dark:text-gray-400 mb-2">
                      Drag & drop files here, or click to select
                    </p>
                    <p className="text-sm text-gray-500 dark:text-gray-500">
                      Multiple files supported
                    </p>
                  </div>
                )}
              </div>

              {/* Upload Progress */}
              {Object.keys(uploadProgress).length > 0 && (
                <div className="mt-4 space-y-2">
                  <h3 className="text-sm font-medium text-gray-900 dark:text-white">
                    Upload Progress
                  </h3>
                  {Object.entries(uploadProgress).map(([filename, progress]) => (
                    <div key={filename} className="space-y-1">
                      <div className="flex justify-between text-sm">
                        <span className="text-gray-600 dark:text-gray-400 truncate">
                          {filename}
                        </span>
                        <span className="text-gray-900 dark:text-white">
                          {progress}%
                        </span>
                      </div>
                      <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
                        <div
                          className="bg-primary-600 h-2 rounded-full transition-all duration-300"
                          style={{ width: `${progress}%` }}
                        />
                      </div>
                    </div>
                  ))}
                </div>
              )}

              <div className="mt-6 flex justify-end">
                <button
                  onClick={() => setShowUploadModal(false)}
                  className="btn-outline"
                  disabled={uploadMutation.isPending}
                >
                  {uploadMutation.isPending ? 'Uploading...' : 'Close'}
                </button>
              </div>
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
                Delete Object
              </h2>
              <p className="text-gray-600 dark:text-gray-400 mb-6">
                Are you sure you want to delete "{deleteConfirm}"? This action cannot be undone.
              </p>
              <div className="flex space-x-3">
                <button
                  onClick={() => setDeleteConfirm(null)}
                  className="btn-outline flex-1"
                >
                  Cancel
                </button>
                <button
                  onClick={() => handleDelete(deleteConfirm)}
                  disabled={deleteMutation.isPending}
                  className="btn-danger flex-1"
                >
                  {deleteMutation.isPending ? (
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