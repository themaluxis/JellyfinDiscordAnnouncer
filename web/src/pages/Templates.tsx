export default function Templates() {
  return (
    <div className="px-4 sm:px-6 lg:px-8">
      <div className="sm:flex sm:items-center">
        <div className="sm:flex-auto">
          <h1 className="text-2xl font-semibold leading-6 text-gray-900">Templates</h1>
          <p className="mt-2 text-sm text-gray-700">
            Customize Discord embed templates with Jinja2 syntax.
          </p>
        </div>
      </div>

      <div className="mt-8">
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          <div className="card">
            <h3 className="text-lg font-medium leading-6 text-gray-900 mb-4">Available Templates</h3>
            <div className="space-y-2">
              <button className="w-full text-left px-3 py-2 text-sm bg-gray-50 hover:bg-gray-100 rounded-md">
                new_item.j2 - New items added
              </button>
              <button className="w-full text-left px-3 py-2 text-sm bg-gray-50 hover:bg-gray-100 rounded-md">
                upgraded_item.j2 - Quality upgrades
              </button>
              <button className="w-full text-left px-3 py-2 text-sm bg-gray-50 hover:bg-gray-100 rounded-md">
                deleted_item.j2 - Item deletions
              </button>
              <button className="w-full text-left px-3 py-2 text-sm bg-gray-50 hover:bg-gray-100 rounded-md">
                new_items_grouped.j2 - Grouped new items
              </button>
            </div>
          </div>

          <div className="card">
            <h3 className="text-lg font-medium leading-6 text-gray-900 mb-4">Template Editor</h3>
            <div className="space-y-4">
              <div>
                <label htmlFor="template-name" className="label">
                  Template: new_item.j2
                </label>
              </div>
              <div>
                <textarea
                  id="template-content"
                  name="template-content"
                  rows={12}
                  className="input font-mono text-sm"
                  defaultValue={`{
  "embeds": [{
    "title": "🎬 New {{ item.type }} Added",
    "description": "**{{ item.name }}**{% if item.year %} ({{ item.year }}){% endif %}",
    "color": 6736947,
    "timestamp": "{{ now().isoformat() }}"
  }]
}`}
                />
              </div>
              <div className="flex justify-between">
                <button type="button" className="btn btn-secondary px-3 py-2">
                  Validate
                </button>
                <div className="space-x-2">
                  <button type="button" className="btn btn-secondary px-3 py-2">
                    Reset
                  </button>
                  <button type="button" className="btn btn-primary px-3 py-2">
                    Save
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div className="mt-8 card">
          <h3 className="text-lg font-medium leading-6 text-gray-900 mb-4">Template Variables</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div>
              <h4 className="font-medium text-gray-900 mb-2">Item Properties</h4>
              <ul className="text-sm text-gray-600 space-y-1">
                <li><code className="bg-gray-100 px-1 rounded">item.name</code> - Item name</li>
                <li><code className="bg-gray-100 px-1 rounded">item.type</code> - Content type (Movie, Series, etc.)</li>
                <li><code className="bg-gray-100 px-1 rounded">item.year</code> - Release year</li>
                <li><code className="bg-gray-100 px-1 rounded">item.overview</code> - Plot summary</li>
                <li><code className="bg-gray-100 px-1 rounded">item.genres</code> - Genre list</li>
                <li><code className="bg-gray-100 px-1 rounded">item.resolution</code> - Video resolution</li>
              </ul>
            </div>
            <div>
              <h4 className="font-medium text-gray-900 mb-2">Custom Filters</h4>
              <ul className="text-sm text-gray-600 space-y-1">
                <li><code className="bg-gray-100 px-1 rounded">format_runtime</code> - Format runtime ticks</li>
                <li><code className="bg-gray-100 px-1 rounded">format_file_size</code> - Format file size</li>
                <li><code className="bg-gray-100 px-1 rounded">truncate_text</code> - Truncate long text</li>
                <li><code className="bg-gray-100 px-1 rounded">discord_timestamp</code> - Discord timestamp format</li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}