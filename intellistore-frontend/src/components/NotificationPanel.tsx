import React from 'react'
import { motion } from 'framer-motion'
import { XMarkIcon, CheckIcon, TrashIcon } from '@heroicons/react/24/outline'
import { useWebSocket } from '../hooks/useWebSocket'
import { formatDistanceToNow } from '../utils/date'
import clsx from 'clsx'

interface NotificationPanelProps {
  onClose: () => void
}

export default function NotificationPanel({ onClose }: NotificationPanelProps) {
  const { notifications, markNotificationAsRead, clearNotifications } = useWebSocket()

  const handleMarkAsRead = (id: string) => {
    markNotificationAsRead(id)
  }

  const handleMarkAllAsRead = () => {
    notifications.forEach((notification) => {
      if (!notification.read) {
        markNotificationAsRead(notification.id)
      }
    })
  }

  const getNotificationIcon = (type: string) => {
    switch (type) {
      case 'success':
        return '✅'
      case 'warning':
        return '⚠️'
      case 'error':
        return '❌'
      default:
        return 'ℹ️'
    }
  }

  return (
    <motion.div
      initial={{ x: '100%' }}
      animate={{ x: 0 }}
      exit={{ x: '100%' }}
      transition={{ type: 'spring', stiffness: 300, damping: 30 }}
      className="fixed inset-y-0 right-0 z-50 w-96 bg-white dark:bg-gray-800 shadow-xl border-l border-gray-200 dark:border-gray-700"
    >
      <div className="flex flex-col h-full">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
            Notifications
          </h2>
          <div className="flex items-center space-x-2">
            {notifications.length > 0 && (
              <>
                <button
                  onClick={handleMarkAllAsRead}
                  className="p-1 text-gray-400 hover:text-gray-500 dark:hover:text-gray-300"
                  title="Mark all as read"
                >
                  <CheckIcon className="h-5 w-5" />
                </button>
                <button
                  onClick={clearNotifications}
                  className="p-1 text-gray-400 hover:text-gray-500 dark:hover:text-gray-300"
                  title="Clear all"
                >
                  <TrashIcon className="h-5 w-5" />
                </button>
              </>
            )}
            <button
              onClick={onClose}
              className="p-1 text-gray-400 hover:text-gray-500 dark:hover:text-gray-300"
            >
              <XMarkIcon className="h-5 w-5" />
            </button>
          </div>
        </div>

        {/* Notifications list */}
        <div className="flex-1 overflow-y-auto">
          {notifications.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full text-gray-500 dark:text-gray-400">
              <div className="text-4xl mb-2">🔔</div>
              <p className="text-sm">No notifications</p>
            </div>
          ) : (
            <div className="space-y-1 p-2">
              {notifications.map((notification) => (
                <motion.div
                  key={notification.id}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  className={clsx(
                    'p-3 rounded-lg border cursor-pointer transition-colors',
                    notification.read
                      ? 'bg-gray-50 dark:bg-gray-700 border-gray-200 dark:border-gray-600'
                      : 'bg-white dark:bg-gray-800 border-primary-200 dark:border-primary-700 shadow-sm'
                  )}
                  onClick={() => handleMarkAsRead(notification.id)}
                >
                  <div className="flex items-start space-x-3">
                    <div className="flex-shrink-0 text-lg">
                      {getNotificationIcon(notification.type)}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between">
                        <p
                          className={clsx(
                            'text-sm font-medium',
                            notification.read
                              ? 'text-gray-600 dark:text-gray-400'
                              : 'text-gray-900 dark:text-white'
                          )}
                        >
                          {notification.title}
                        </p>
                        {!notification.read && (
                          <div className="w-2 h-2 bg-primary-500 rounded-full flex-shrink-0" />
                        )}
                      </div>
                      <p
                        className={clsx(
                          'text-sm mt-1',
                          notification.read
                            ? 'text-gray-500 dark:text-gray-500'
                            : 'text-gray-700 dark:text-gray-300'
                        )}
                      >
                        {notification.message}
                      </p>
                      <p className="text-xs text-gray-400 dark:text-gray-500 mt-2">
                        {formatDistanceToNow(new Date(notification.timestamp))} ago
                      </p>
                    </div>
                  </div>
                </motion.div>
              ))}
            </div>
          )}
        </div>
      </div>
    </motion.div>
  )
}