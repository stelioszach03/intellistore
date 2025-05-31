import React, { ReactNode, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import Sidebar from './Sidebar'
import Header from './Header'
import NotificationPanel from './NotificationPanel'

interface LayoutProps {
  children: ReactNode
}

export default function Layout({ children }: LayoutProps) {
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [notificationPanelOpen, setNotificationPanelOpen] = useState(false)

  return (
    <div className="flex h-screen bg-gray-50 dark:bg-gray-900">
      {/* Sidebar */}
      <Sidebar open={sidebarOpen} onClose={() => setSidebarOpen(false)} />

      {/* Main content */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Header */}
        <Header
          onMenuClick={() => setSidebarOpen(true)}
          onNotificationClick={() => setNotificationPanelOpen(true)}
        />

        {/* Page content */}
        <main className="flex-1 overflow-auto">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3 }}
            className="p-6"
          >
            {children}
          </motion.div>
        </main>
      </div>

      {/* Notification panel */}
      <AnimatePresence>
        {notificationPanelOpen && (
          <NotificationPanel onClose={() => setNotificationPanelOpen(false)} />
        )}
      </AnimatePresence>

      {/* Mobile sidebar overlay */}
      <AnimatePresence>
        {sidebarOpen && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-40 bg-black bg-opacity-50 lg:hidden"
            onClick={() => setSidebarOpen(false)}
          />
        )}
      </AnimatePresence>
    </div>
  )
}