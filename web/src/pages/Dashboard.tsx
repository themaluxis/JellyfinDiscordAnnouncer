import { useEffect } from 'react'
import { useAppStore } from '@/store/appStore'
import {
  ChartBarIcon,
  CloudArrowDownIcon,
  CpuChipIcon,
  GlobeAltIcon,
} from '@heroicons/react/24/outline'

const stats = [
  { name: 'Total Items', value: '1,234', icon: ChartBarIcon, change: '+12%', changeType: 'positive' },
  { name: 'Notifications Sent', value: '2,468', icon: CloudArrowDownIcon, change: '+5%', changeType: 'positive' },
  { name: 'Queue Size', value: '0', icon: CpuChipIcon, change: 'Healthy', changeType: 'neutral' },
  { name: 'Uptime', value: '15d 3h', icon: GlobeAltIcon, change: '99.9%', changeType: 'positive' },
]

export default function Dashboard() {
  const { loadStats, loadHealth } = useAppStore()

  useEffect(() => {
    loadStats()
    loadHealth()
  }, [loadStats, loadHealth])

  return (
    <div className="px-4 sm:px-6 lg:px-8">
      <div className="sm:flex sm:items-center">
        <div className="sm:flex-auto">
          <h1 className="text-2xl font-semibold leading-6 text-gray-900">Dashboard</h1>
          <p className="mt-2 text-sm text-gray-700">
            Overview of your Jellynouncer service status and statistics.
          </p>
        </div>
        <div className="mt-4 sm:ml-16 sm:mt-0 sm:flex-none">
          <button
            type="button"
            className="btn btn-primary px-3 py-2"
          >
            Test Webhook
          </button>
        </div>
      </div>

      <div className="mt-8">
        <div className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
          {stats.map((item) => (
            <div key={item.name} className="card">
              <div className="flex items-center">
                <div className="flex-shrink-0">
                  <item.icon className="h-6 w-6 text-gray-400" aria-hidden="true" />
                </div>
                <div className="ml-5 w-0 flex-1">
                  <dl>
                    <dt className="text-sm font-medium text-gray-500 truncate">{item.name}</dt>
                    <dd className="flex items-baseline">
                      <div className="text-2xl font-semibold text-gray-900">{item.value}</div>
                      <div className="ml-2 flex items-baseline text-sm">
                        <span className="text-gray-500">{item.change}</span>
                      </div>
                    </dd>
                  </dl>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="mt-8 grid grid-cols-1 gap-8 lg:grid-cols-2">
        <div className="card">
          <h3 className="text-lg font-medium leading-6 text-gray-900 mb-4">Recent Activity</h3>
          <div className="space-y-3">
            <div className="flex items-center space-x-3">
              <div className="h-2 w-2 bg-green-400 rounded-full"></div>
              <span className="text-sm text-gray-600">New movie added: "Dune: Part Two"</span>
              <span className="text-xs text-gray-400">2 min ago</span>
            </div>
            <div className="flex items-center space-x-3">
              <div className="h-2 w-2 bg-blue-400 rounded-full"></div>
              <span className="text-sm text-gray-600">Quality upgrade: "The Matrix" 1080p → 4K</span>
              <span className="text-xs text-gray-400">15 min ago</span>
            </div>
            <div className="flex items-center space-x-3">
              <div className="h-2 w-2 bg-green-400 rounded-full"></div>
              <span className="text-sm text-gray-600">New episode added: "The Expanse S06E06"</span>
              <span className="text-xs text-gray-400">1 hour ago</span>
            </div>
          </div>
        </div>

        <div className="card">
          <h3 className="text-lg font-medium leading-6 text-gray-900 mb-4">System Health</h3>
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-600">Jellyfin Connection</span>
              <span className="inline-flex items-center rounded-full bg-green-100 px-2.5 py-0.5 text-xs font-medium text-green-800">
                Connected
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-600">Discord Webhooks</span>
              <span className="inline-flex items-center rounded-full bg-green-100 px-2.5 py-0.5 text-xs font-medium text-green-800">
                Active
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-600">Database</span>
              <span className="inline-flex items-center rounded-full bg-green-100 px-2.5 py-0.5 text-xs font-medium text-green-800">
                Healthy
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-600">External APIs</span>
              <span className="inline-flex items-center rounded-full bg-yellow-100 px-2.5 py-0.5 text-xs font-medium text-yellow-800">
                Partial
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}