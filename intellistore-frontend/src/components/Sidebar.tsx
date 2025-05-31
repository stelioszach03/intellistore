import React from 'react'
import { NavLink, useLocation } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import {
  HomeIcon,
  FolderIcon,
  ChartBarIcon,
  CogIcon,
  XMarkIcon,
} from '@heroicons/react/24/outline'
import clsx from 'clsx'

interface SidebarProps {
  open: boolean
  onClose: () => void
}

const navigation = [
  { name: 'Dashboard', href: '/dashboard', icon: HomeIcon },
  { name: 'Buckets', href: '/buckets', icon: FolderIcon },
  { name: 'Metrics', href: '/metrics', icon: ChartBarIcon },
  { name: 'Settings', href: '/settings', icon: CogIcon },
]

export default function Sidebar({ open, onClose }: SidebarProps) {
  const location = useLocation()

  const sidebarVariants = {
    open: {
      x: 0,
      transition: {
        type: 'spring',
        stiffness: 300,
        damping: 30,
      },
    },
    closed: {
      x: '-100%',
      transition: {
        type: 'spring',
        stiffness: 300,
        damping: 30,
      },
    },
  }

  return (
    <>
      {/* Desktop sidebar */}
      <div className="hidden lg:flex lg:flex-shrink-0">
        <div className="flex flex-col w-64">
          <div className="flex flex-col flex-grow bg-white dark:bg-gray-800 border-r border-gray-200 dark:border-gray-700 pt-5 pb-4 overflow-y-auto">
            <div className="flex items-center flex-shrink-0 px-4">
              <div className="flex items-center">
                <div className="w-8 h-8 bg-gradient-to-r from-primary-600 to-secondary-600 rounded-lg flex items-center justify-center">
                  <span className="text-white font-bold text-lg">I</span>
                </div>
                <span className="ml-3 text-xl font-semibold text-gray-900 dark:text-white">
                  IntelliStore
                </span>
              </div>
            </div>
            <div className="mt-5 flex-grow flex flex-col">
              <nav className="flex-1 px-2 space-y-1">
                {navigation.map((item) => {
                  const isActive = location.pathname === item.href
                  return (
                    <NavLink
                      key={item.name}
                      to={item.href}
                      className={clsx(
                        isActive ? 'sidebar-link-active' : 'sidebar-link-inactive',
                        'group flex items-center px-2 py-2 text-sm font-medium rounded-md'
                      )}
                    >
                      <item.icon
                        className={clsx(
                          isActive
                            ? 'text-primary-500'
                            : 'text-gray-400 group-hover:text-gray-500 dark:group-hover:text-gray-300',
                          'mr-3 flex-shrink-0 h-6 w-6'
                        )}
                        aria-hidden="true"
                      />
                      {item.name}
                    </NavLink>
                  )
                })}
              </nav>
            </div>
          </div>
        </div>
      </div>

      {/* Mobile sidebar */}
      <AnimatePresence>
        {open && (
          <motion.div
            initial="closed"
            animate="open"
            exit="closed"
            variants={sidebarVariants}
            className="fixed inset-y-0 left-0 z-50 w-64 bg-white dark:bg-gray-800 border-r border-gray-200 dark:border-gray-700 lg:hidden"
          >
            <div className="flex flex-col h-full">
              <div className="flex items-center justify-between h-16 px-4 border-b border-gray-200 dark:border-gray-700">
                <div className="flex items-center">
                  <div className="w-8 h-8 bg-gradient-to-r from-primary-600 to-secondary-600 rounded-lg flex items-center justify-center">
                    <span className="text-white font-bold text-lg">I</span>
                  </div>
                  <span className="ml-3 text-xl font-semibold text-gray-900 dark:text-white">
                    IntelliStore
                  </span>
                </div>
                <button
                  onClick={onClose}
                  className="p-2 rounded-md text-gray-400 hover:text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-primary-500"
                >
                  <XMarkIcon className="h-6 w-6" />
                </button>
              </div>
              <div className="flex-1 px-2 py-4 space-y-1 overflow-y-auto">
                {navigation.map((item) => {
                  const isActive = location.pathname === item.href
                  return (
                    <NavLink
                      key={item.name}
                      to={item.href}
                      onClick={onClose}
                      className={clsx(
                        isActive ? 'sidebar-link-active' : 'sidebar-link-inactive',
                        'group flex items-center px-2 py-2 text-sm font-medium rounded-md'
                      )}
                    >
                      <item.icon
                        className={clsx(
                          isActive
                            ? 'text-primary-500'
                            : 'text-gray-400 group-hover:text-gray-500 dark:group-hover:text-gray-300',
                          'mr-3 flex-shrink-0 h-6 w-6'
                        )}
                        aria-hidden="true"
                      />
                      {item.name}
                    </NavLink>
                  )
                })}
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  )
}