import React, { Fragment } from 'react'
import { Menu, Transition } from '@headlessui/react'
import {
  Bars3Icon,
  BellIcon,
  SunIcon,
  MoonIcon,
  ComputerDesktopIcon,
} from '@heroicons/react/24/outline'
import { useAuth } from '../hooks/useAuth'
import { useTheme } from '../hooks/useTheme'
import { useWebSocket } from '../hooks/useWebSocket'
import clsx from 'clsx'

interface HeaderProps {
  onMenuClick: () => void
  onNotificationClick: () => void
}

export default function Header({ onMenuClick, onNotificationClick }: HeaderProps) {
  const { user, logout } = useAuth()
  const { theme, setTheme, isDark } = useTheme()
  const { notifications, isConnected } = useWebSocket()

  const unreadCount = notifications.filter((n) => !n.read).length

  const themeOptions = [
    { value: 'light', label: 'Light', icon: SunIcon },
    { value: 'dark', label: 'Dark', icon: MoonIcon },
    { value: 'system', label: 'System', icon: ComputerDesktopIcon },
  ]

  return (
    <header className="bg-white dark:bg-gray-800 shadow-sm border-b border-gray-200 dark:border-gray-700">
      <div className="flex items-center justify-between h-16 px-4 sm:px-6 lg:px-8">
        {/* Left side */}
        <div className="flex items-center">
          <button
            onClick={onMenuClick}
            className="p-2 rounded-md text-gray-400 hover:text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-primary-500 lg:hidden"
          >
            <Bars3Icon className="h-6 w-6" />
          </button>
        </div>

        {/* Right side */}
        <div className="flex items-center space-x-4">
          {/* WebSocket status indicator */}
          <div className="flex items-center space-x-2">
            <div
              className={clsx(
                'w-2 h-2 rounded-full',
                isConnected ? 'bg-green-500' : 'bg-red-500'
              )}
            />
            <span className="text-xs text-gray-500 dark:text-gray-400 hidden sm:block">
              {isConnected ? 'Connected' : 'Disconnected'}
            </span>
          </div>

          {/* Theme selector */}
          <Menu as="div" className="relative">
            <Menu.Button className="p-2 rounded-md text-gray-400 hover:text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-primary-500">
              {isDark ? (
                <MoonIcon className="h-5 w-5" />
              ) : (
                <SunIcon className="h-5 w-5" />
              )}
            </Menu.Button>
            <Transition
              as={Fragment}
              enter="transition ease-out duration-100"
              enterFrom="transform opacity-0 scale-95"
              enterTo="transform opacity-100 scale-100"
              leave="transition ease-in duration-75"
              leaveFrom="transform opacity-100 scale-100"
              leaveTo="transform opacity-0 scale-95"
            >
              <Menu.Items className="absolute right-0 z-10 mt-2 w-48 origin-top-right rounded-md bg-white dark:bg-gray-800 py-1 shadow-lg ring-1 ring-black ring-opacity-5 focus:outline-none">
                {themeOptions.map((option) => (
                  <Menu.Item key={option.value}>
                    {({ active }) => (
                      <button
                        onClick={() => setTheme(option.value as any)}
                        className={clsx(
                          active
                            ? 'bg-gray-100 dark:bg-gray-700'
                            : '',
                          theme === option.value
                            ? 'text-primary-600 dark:text-primary-400'
                            : 'text-gray-700 dark:text-gray-300',
                          'flex w-full items-center px-4 py-2 text-sm'
                        )}
                      >
                        <option.icon className="mr-3 h-4 w-4" />
                        {option.label}
                      </button>
                    )}
                  </Menu.Item>
                ))}
              </Menu.Items>
            </Transition>
          </Menu>

          {/* Notifications */}
          <button
            onClick={onNotificationClick}
            className="relative p-2 rounded-md text-gray-400 hover:text-gray-500 hover:bg-gray-100 dark:hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-primary-500"
          >
            <BellIcon className="h-5 w-5" />
            {unreadCount > 0 && (
              <span className="absolute -top-1 -right-1 h-4 w-4 bg-red-500 text-white text-xs rounded-full flex items-center justify-center">
                {unreadCount > 9 ? '9+' : unreadCount}
              </span>
            )}
          </button>

          {/* User menu */}
          <Menu as="div" className="relative">
            <Menu.Button className="flex items-center space-x-3 text-sm rounded-full focus:outline-none focus:ring-2 focus:ring-primary-500">
              <div className="w-8 h-8 bg-gradient-to-r from-primary-600 to-secondary-600 rounded-full flex items-center justify-center">
                <span className="text-white font-medium text-sm">
                  {user?.username?.charAt(0).toUpperCase()}
                </span>
              </div>
              <span className="hidden md:block text-gray-700 dark:text-gray-300 font-medium">
                {user?.username}
              </span>
            </Menu.Button>
            <Transition
              as={Fragment}
              enter="transition ease-out duration-100"
              enterFrom="transform opacity-0 scale-95"
              enterTo="transform opacity-100 scale-100"
              leave="transition ease-in duration-75"
              leaveFrom="transform opacity-100 scale-100"
              leaveTo="transform opacity-0 scale-95"
            >
              <Menu.Items className="absolute right-0 z-10 mt-2 w-48 origin-top-right rounded-md bg-white dark:bg-gray-800 py-1 shadow-lg ring-1 ring-black ring-opacity-5 focus:outline-none">
                <div className="px-4 py-2 border-b border-gray-200 dark:border-gray-700">
                  <p className="text-sm text-gray-700 dark:text-gray-300">{user?.email}</p>
                  <p className="text-xs text-gray-500 dark:text-gray-400 capitalize">
                    {user?.role}
                  </p>
                </div>
                <Menu.Item>
                  {({ active }) => (
                    <button
                      onClick={logout}
                      className={clsx(
                        active ? 'bg-gray-100 dark:bg-gray-700' : '',
                        'block w-full text-left px-4 py-2 text-sm text-gray-700 dark:text-gray-300'
                      )}
                    >
                      Sign out
                    </button>
                  )}
                </Menu.Item>
              </Menu.Items>
            </Transition>
          </Menu>
        </div>
      </div>
    </header>
  )
}