import React from 'react'
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Toaster } from 'react-hot-toast'
import { AuthProvider } from './hooks/useAuth'
import { ThemeProvider } from './hooks/useTheme'
import { WebSocketProvider } from './hooks/useWebSocket'
import Layout from './components/Layout'
import LoginPage from './pages/LoginPage'
import DashboardPage from './pages/DashboardPage'
import BucketsPage from './pages/BucketsPage'
import ObjectsPage from './pages/ObjectsPage'
import MetricsPage from './pages/MetricsPage'
import SettingsPage from './pages/SettingsPage'
import ProtectedRoute from './components/ProtectedRoute'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      staleTime: 5 * 60 * 1000, // 5 minutes
    },
  },
})

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider>
        <AuthProvider>
          <WebSocketProvider>
            <Router>
              <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
                <Routes>
                  <Route path="/login" element={<LoginPage />} />
                  <Route
                    path="/*"
                    element={
                      <ProtectedRoute>
                        <Layout>
                          <Routes>
                            <Route path="/" element={<Navigate to="/dashboard" replace />} />
                            <Route path="/dashboard" element={<DashboardPage />} />
                            <Route path="/buckets" element={<BucketsPage />} />
                            <Route path="/buckets/:bucketName/objects" element={<ObjectsPage />} />
                            <Route path="/metrics" element={<MetricsPage />} />
                            <Route path="/settings" element={<SettingsPage />} />
                          </Routes>
                        </Layout>
                      </ProtectedRoute>
                    }
                  />
                </Routes>
                <Toaster
                  position="top-right"
                  toastOptions={{
                    duration: 4000,
                    style: {
                      background: 'var(--toast-bg)',
                      color: 'var(--toast-color)',
                      border: '1px solid var(--toast-border)',
                    },
                  }}
                />
              </div>
            </Router>
          </WebSocketProvider>
        </AuthProvider>
      </ThemeProvider>
    </QueryClientProvider>
  )
}

export default App