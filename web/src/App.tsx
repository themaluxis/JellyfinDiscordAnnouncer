import { Routes, Route, Navigate } from 'react-router-dom'
import Layout from '@/components/Layout'
import Dashboard from '@/pages/Dashboard'
import Configuration from '@/pages/Configuration'
import Templates from '@/pages/Templates'
import Logs from '@/pages/Logs'
import { useAppStore } from '@/store/appStore'
import { useEffect } from 'react'

function App() {
  const { loadConfig, loading } = useAppStore()

  useEffect(() => {
    loadConfig()
  }, [loadConfig])

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="w-16 h-16 border-4 border-jellyfin-600 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <h2 className="text-lg font-medium text-gray-900">Loading Jellynouncer...</h2>
        </div>
      </div>
    )
  }

  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/configuration" element={<Configuration />} />
        <Route path="/templates" element={<Templates />} />
        <Route path="/logs" element={<Logs />} />
      </Routes>
    </Layout>
  )
}

export default App