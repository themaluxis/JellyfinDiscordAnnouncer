export default function Logs() {
  const logs = [
    {
      id: 1,
      timestamp: '2024-01-15 14:30:25',
      level: 'INFO',
      message: 'Received webhook: ItemAdded for "Dune: Part Two"',
    },
    {
      id: 2,
      timestamp: '2024-01-15 14:30:26',
      level: 'INFO',
      message: 'Sent new item notification: Dune: Part Two',
    },
    {
      id: 3,
      timestamp: '2024-01-15 14:25:12',
      level: 'INFO',
      message: 'Detected upgrade: The Matrix 1080p → 4K',
    },
    {
      id: 4,
      timestamp: '2024-01-15 14:20:45',
      level: 'WARNING',
      message: 'Rate limited for 1.2s on webhook',
    },
    {
      id: 5,
      timestamp: '2024-01-15 14:15:30',
      level: 'ERROR',
      message: 'Failed to connect to external API: TMDb timeout',
    },
  ]

  const getLevelColor = (level: string) => {
    switch (level) {
      case 'ERROR':
        return 'bg-red-100 text-red-800'
      case 'WARNING':
        return 'bg-yellow-100 text-yellow-800'
      case 'INFO':
        return 'bg-blue-100 text-blue-800'
      case 'DEBUG':
        return 'bg-gray-100 text-gray-800'
      default:
        return 'bg-gray-100 text-gray-800'
    }
  }

  return (
    <div className="px-4 sm:px-6 lg:px-8">
      <div className="sm:flex sm:items-center">
        <div className="sm:flex-auto">
          <h1 className="text-2xl font-semibold leading-6 text-gray-900">Logs</h1>
          <p className="mt-2 text-sm text-gray-700">
            View application logs and troubleshoot issues.
          </p>
        </div>
        <div className="mt-4 sm:ml-16 sm:mt-0 sm:flex-none space-x-2">
          <select className="input text-sm">
            <option>All Levels</option>
            <option>ERROR</option>
            <option>WARNING</option>
            <option>INFO</option>
            <option>DEBUG</option>
          </select>
          <button type="button" className="btn btn-secondary px-3 py-2 text-sm">
            Refresh
          </button>
          <button type="button" className="btn btn-primary px-3 py-2 text-sm">
            Download
          </button>
        </div>
      </div>

      <div className="mt-8">
        <div className="card p-0">
          <div className="px-6 py-4 border-b border-gray-200">
            <h3 className="text-lg font-medium leading-6 text-gray-900">Recent Logs</h3>
          </div>
          <div className="divide-y divide-gray-200">
            {logs.map((log) => (
              <div key={log.id} className="px-6 py-4 hover:bg-gray-50">
                <div className="flex items-start space-x-3">
                  <span className="text-sm text-gray-500 font-mono min-w-[140px]">
                    {log.timestamp}
                  </span>
                  <span
                    className={`inline-flex rounded-full px-2 text-xs font-semibold leading-5 min-w-[60px] justify-center ${getLevelColor(
                      log.level
                    )}`}
                  >
                    {log.level}
                  </span>
                  <span className="text-sm text-gray-900 flex-1">{log.message}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="mt-8 grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="card">
          <h3 className="text-lg font-medium leading-6 text-gray-900 mb-4">Log Statistics</h3>
          <div className="space-y-3">
            <div className="flex justify-between">
              <span className="text-sm text-gray-600">Total entries today</span>
              <span className="text-sm font-medium">1,234</span>
            </div>
            <div className="flex justify-between">
              <span className="text-sm text-gray-600">Errors</span>
              <span className="text-sm font-medium text-red-600">3</span>
            </div>
            <div className="flex justify-between">
              <span className="text-sm text-gray-600">Warnings</span>
              <span className="text-sm font-medium text-yellow-600">12</span>
            </div>
            <div className="flex justify-between">
              <span className="text-sm text-gray-600">Log file size</span>
              <span className="text-sm font-medium">2.3 MB</span>
            </div>
          </div>
        </div>

        <div className="card lg:col-span-2">
          <h3 className="text-lg font-medium leading-6 text-gray-900 mb-4">Log Files</h3>
          <div className="space-y-2">
            <div className="flex items-center justify-between p-3 bg-gray-50 rounded-md">
              <div>
                <span className="text-sm font-medium">jellynouncer.log</span>
                <span className="text-xs text-gray-500 block">Main application log</span>
              </div>
              <div className="flex space-x-2">
                <button className="text-sm text-jellyfin-600 hover:text-jellyfin-700">View</button>
                <button className="text-sm text-jellyfin-600 hover:text-jellyfin-700">Download</button>
              </div>
            </div>
            <div className="flex items-center justify-between p-3 bg-gray-50 rounded-md">
              <div>
                <span className="text-sm font-medium">jellynouncer-debug.log</span>
                <span className="text-xs text-gray-500 block">Debug log (verbose)</span>
              </div>
              <div className="flex space-x-2">
                <button className="text-sm text-jellyfin-600 hover:text-jellyfin-700">View</button>
                <button className="text-sm text-jellyfin-600 hover:text-jellyfin-700">Download</button>
              </div>
            </div>
            <div className="flex items-center justify-between p-3 bg-gray-50 rounded-md">
              <div>
                <span className="text-sm font-medium">jellynouncer-error.log</span>
                <span className="text-xs text-gray-500 block">Error-only log</span>
              </div>
              <div className="flex space-x-2">
                <button className="text-sm text-jellyfin-600 hover:text-jellyfin-700">View</button>
                <button className="text-sm text-jellyfin-600 hover:text-jellyfin-700">Download</button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}