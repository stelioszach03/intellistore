import React from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
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

function App() {
  return (
    <ThemeProvider>
      <AuthProvider>
        <WebSocketProvider>
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
          </div>
        </WebSocketProvider>
      </AuthProvider>
    </ThemeProvider>
  )
}

export default App