import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { User } from '../types'
import apiService from '../services/api'
import toast from 'react-hot-toast'

interface AuthContextType {
  user: User | null
  isLoading: boolean
  isAuthenticated: boolean
  login: (username: string, password: string) => Promise<void>
  logout: () => Promise<void>
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

interface AuthProviderProps {
  children: ReactNode
}

export function AuthProvider({ children }: AuthProviderProps) {
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const queryClient = useQueryClient()

  // Check if user is authenticated on mount
  useEffect(() => {
    const token = apiService.getStoredToken()
    setIsAuthenticated(!!token)
  }, [])

  // Get current user
  const {
    data: user,
    isLoading,
    error,
  } = useQuery({
    queryKey: ['currentUser'],
    queryFn: apiService.getCurrentUser,
    enabled: isAuthenticated,
    retry: false,
    staleTime: 5 * 60 * 1000, // 5 minutes
  })

  // Handle auth error
  useEffect(() => {
    if (error) {
      setIsAuthenticated(false)
      apiService.clearToken()
    }
  }, [error])

  // Login mutation
  const loginMutation = useMutation({
    mutationFn: ({ username, password }: { username: string; password: string }) =>
      apiService.login(username, password),
    onSuccess: (data) => {
      apiService.setToken(data.token)
      setIsAuthenticated(true)
      queryClient.setQueryData(['currentUser'], data.user)
      toast.success('Successfully logged in!')
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.message || 'Login failed')
    },
  })

  // Logout mutation
  const logoutMutation = useMutation({
    mutationFn: apiService.logout,
    onSuccess: () => {
      setIsAuthenticated(false)
      queryClient.clear()
      toast.success('Successfully logged out!')
    },
    onError: () => {
      // Clear local state even if API call fails
      setIsAuthenticated(false)
      apiService.clearToken()
      queryClient.clear()
    },
  })

  const login = async (username: string, password: string) => {
    await loginMutation.mutateAsync({ username, password })
  }

  const logout = async () => {
    await logoutMutation.mutateAsync()
  }

  const value: AuthContextType = {
    user: user || null,
    isLoading: isLoading || loginMutation.isPending || logoutMutation.isPending,
    isAuthenticated,
    login,
    logout,
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}