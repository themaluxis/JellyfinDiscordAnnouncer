export default function Configuration() {
  return (
    <div className="px-4 sm:px-6 lg:px-8">
      <div className="sm:flex sm:items-center">
        <div className="sm:flex-auto">
          <h1 className="text-2xl font-semibold leading-6 text-gray-900">Configuration</h1>
          <p className="mt-2 text-sm text-gray-700">
            Manage your Jellynouncer settings and webhooks.
          </p>
        </div>
      </div>

      <div className="mt-8 space-y-8">
        <div className="card">
          <h3 className="text-lg font-medium leading-6 text-gray-900 mb-4">Jellyfin Settings</h3>
          <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
            <div>
              <label htmlFor="server-url" className="label">
                Server URL
              </label>
              <input
                type="url"
                name="server-url"
                id="server-url"
                className="input mt-1"
                placeholder="http://jellyfin:8096"
              />
            </div>
            <div>
              <label htmlFor="api-key" className="label">
                API Key
              </label>
              <input
                type="password"
                name="api-key"
                id="api-key"
                className="input mt-1"
                placeholder="Your Jellyfin API key"
              />
            </div>
          </div>
        </div>

        <div className="card">
          <h3 className="text-lg font-medium leading-6 text-gray-900 mb-4">Discord Webhooks</h3>
          <div className="space-y-4">
            <div>
              <label htmlFor="default-webhook" className="label">
                Default Webhook URL
              </label>
              <input
                type="url"
                name="default-webhook"
                id="default-webhook"
                className="input mt-1"
                placeholder="https://discord.com/api/webhooks/..."
              />
            </div>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
              <div>
                <label htmlFor="movies-webhook" className="label">
                  Movies Webhook
                </label>
                <input
                  type="url"
                  name="movies-webhook"
                  id="movies-webhook"
                  className="input mt-1"
                  placeholder="Optional"
                />
              </div>
              <div>
                <label htmlFor="tv-webhook" className="label">
                  TV Shows Webhook
                </label>
                <input
                  type="url"
                  name="tv-webhook"
                  id="tv-webhook"
                  className="input mt-1"
                  placeholder="Optional"
                />
              </div>
              <div>
                <label htmlFor="music-webhook" className="label">
                  Music Webhook
                </label>
                <input
                  type="url"
                  name="music-webhook"
                  id="music-webhook"
                  className="input mt-1"
                  placeholder="Optional"
                />
              </div>
            </div>
          </div>
        </div>

        <div className="card">
          <h3 className="text-lg font-medium leading-6 text-gray-900 mb-4">Notification Settings</h3>
          <div className="space-y-4">
            <div className="flex items-center">
              <input
                id="filter-renames"
                name="filter-renames"
                type="checkbox"
                className="h-4 w-4 text-jellyfin-600 focus:ring-jellyfin-500 border-gray-300 rounded"
                defaultChecked
              />
              <label htmlFor="filter-renames" className="ml-2 block text-sm text-gray-900">
                Filter file renames
              </label>
            </div>
            <div className="flex items-center">
              <input
                id="filter-deletes"
                name="filter-deletes"
                type="checkbox"
                className="h-4 w-4 text-jellyfin-600 focus:ring-jellyfin-500 border-gray-300 rounded"
                defaultChecked
              />
              <label htmlFor="filter-deletes" className="ml-2 block text-sm text-gray-900">
                Filter deletion notifications (for upgrades)
              </label>
            </div>
          </div>
        </div>

        <div className="flex justify-end space-x-3">
          <button type="button" className="btn btn-secondary px-4 py-2">
            Cancel
          </button>
          <button type="button" className="btn btn-primary px-4 py-2">
            Save Configuration
          </button>
        </div>
      </div>
    </div>
  )
}