import React, { createContext, useContext, useEffect, useState, ReactNode } from 'react'
import { io, Socket } from 'socket.io-client'
import { WebSocketMessage, Notification } from '../types'
import { useAuth } from './useAuth'
import toast from 'react-hot-toast'

interface WebSocketContextType {
  socket: Socket | null
  isConnected: boolean
  notifications: Notification[]
  markNotificationAsRead: (id: string) => void
  clearNotifications: () => void
}

const WebSocketContext = createContext<WebSocketContextType | undefined>(undefined)

interface WebSocketProviderProps {
  children: ReactNode
}

export function WebSocketProvider({ children }: WebSocketProviderProps) {
  const [socket, setSocket] = useState<Socket | null>(null)
  const [isConnected, setIsConnected] = useState(false)
  const [notifications, setNotifications] = useState<Notification[]>([])
  const { isAuthenticated, user } = useAuth()

  useEffect(() => {
    if (!isAuthenticated || !user) {
      if (socket) {
        socket.disconnect()
        setSocket(null)
        setIsConnected(false)
      }
      return
    }

    // Simulate connection for now (WebSocket server not implemented yet)
    setIsConnected(true)
    console.log('WebSocket simulation: connected')

    // TODO: Implement actual WebSocket connection when backend supports it
    // const newSocket = io('/ws', {
    //   auth: {
    //     token: localStorage.getItem('intellistore_token'),
    //   },
    //   transports: ['websocket'],
    // })

    return () => {
      setIsConnected(false)
    }
  }, [isAuthenticated, user])

  const handleWebSocketMessage = (message: WebSocketMessage) => {
    switch (message.type) {
      case 'notification':
        handleNotification(message.data)
        break
      case 'upload_progress':
        handleUploadProgress(message.data)
        break
      case 'tier_migration':
        handleTierMigration(message.data)
        break
      case 'alert':
        handleAlert(message.data)
        break
      default:
        console.log('Unknown WebSocket message type:', message.type)
    }
  }

  const handleNotification = (data: any) => {
    const notification: Notification = {
      id: data.id || Date.now().toString(),
      type: data.type || 'info',
      title: data.title,
      message: data.message,
      timestamp: data.timestamp || new Date().toISOString(),
      read: false,
    }

    setNotifications((prev) => [notification, ...prev.slice(0, 49)]) // Keep last 50

    // Show toast notification
    switch (notification.type) {
      case 'success':
        toast.success(notification.message)
        break
      case 'warning':
        toast(notification.message, { icon: '⚠️' })
        break
      case 'error':
        toast.error(notification.message)
        break
      default:
        toast(notification.message)
    }
  }

  const handleUploadProgress = (data: any) => {
    // This could be handled by a specific upload context/hook
    console.log('Upload progress:', data)
  }

  const handleTierMigration = (data: any) => {
    const message = `Object ${data.objectKey} successfully migrated to ${data.targetTier} tier`
    toast.success(message)

    const notification: Notification = {
      id: Date.now().toString(),
      type: 'success',
      title: 'Tier Migration Completed',
      message,
      timestamp: new Date().toISOString(),
      read: false,
    }

    setNotifications((prev) => [notification, ...prev.slice(0, 49)])
  }

  const handleAlert = (data: any) => {
    const notification: Notification = {
      id: data.id || Date.now().toString(),
      type: data.severity === 'critical' ? 'error' : 'warning',
      title: `Alert: ${data.name}`,
      message: data.description,
      timestamp: data.firedAt || new Date().toISOString(),
      read: false,
    }

    setNotifications((prev) => [notification, ...prev.slice(0, 49)])

    // Show persistent toast for critical alerts
    if (data.severity === 'critical') {
      toast.error(notification.message, { duration: 10000 })
    } else {
      toast(notification.message, { icon: '⚠️', duration: 6000 })
    }
  }

  const markNotificationAsRead = (id: string) => {
    setNotifications((prev) =>
      prev.map((notification) =>
        notification.id === id ? { ...notification, read: true } : notification
      )
    )
  }

  const clearNotifications = () => {
    setNotifications([])
  }

  const value: WebSocketContextType = {
    socket,
    isConnected,
    notifications,
    markNotificationAsRead,
    clearNotifications,
  }

  return <WebSocketContext.Provider value={value}>{children}</WebSocketContext.Provider>
}

export function useWebSocket() {
  const context = useContext(WebSocketContext)
  if (context === undefined) {
    throw new Error('useWebSocket must be used within a WebSocketProvider')
  }
  return context
}