# 🔔 Jellynouncer - Docker Hub

**Intelligent Discord notifications for Jellyfin media server with quality upgrade detection and multi-channel routing.**

![Docker Pulls](https://img.shields.io/docker/pulls/themaluxis/jellyfindiscordannouncer)
![Docker Image Size](https://img.shields.io/docker/image-size/themaluxis/jellyfindiscordannouncer)
![Docker Stars](https://img.shields.io/docker/stars/themaluxis/jellyfindiscordannouncer)

## 🚀 Quick Start

### Basic Setup

```bash
docker run -d \
  --name jellynouncer \
  --restart unless-stopped \
  -p 1984:1984 \
  -e JELLYFIN_SERVER_URL=http://jellyfin:8096 \
  -e JELLYFIN_API_KEY=your_api_key \
  -e JELLYFIN_USER_ID=your_user_id \
  -e DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/... \
  -v ./config:/app/config \
  -v ./data:/app/data \
  -v ./logs:/app/logs \
  -v ./templates:/app/templates \
  themaluxis/jellyfindiscordannouncer:latest
```

### Docker Compose (Recommended)

```yaml
version: '3.8'
services:
  jellynouncer:
    image: themaluxis/jellyfindiscordannouncer:latest
    container_name: jellynouncer
    restart: unless-stopped
    ports:
      - "1984:1984"
    environment:
      - JELLYFIN_SERVER_URL=http://jellyfin:8096
      - JELLYFIN_API_KEY=your_api_key
      - JELLYFIN_USER_ID=your_user_id
      - DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
      - TZ=America/New_York
    volumes:
      - ./config:/app/config
      - ./data:/app/data
      - ./logs:/app/logs
      - ./templates:/app/templates
```

## ✨ Key Features

- **🧠 Smart Change Detection**: Distinguishes new content from quality upgrades
- **⬆️ Quality Upgrade Notifications**: Resolution, codec, HDR, and audio improvements
- **🚀 Multi-Channel Routing**: Route movies, TV, and music to different Discord channels
- **🎨 Customizable Templates**: Jinja2 templates for rich Discord embeds
- **📊 External Metadata**: OMDb, TMDb, and TVDb integration for ratings and posters
- **🔄 Background Sync**: Periodic library synchronization
- **💻 Web Interface**: Management dashboard on port 1985
- **🐳 Production Ready**: Health checks, structured logging, graceful shutdown

## 🔧 Configuration

### Required Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `JELLYFIN_SERVER_URL` | Jellyfin server URL | `http://jellyfin:8096` |
| `JELLYFIN_API_KEY` | Jellyfin API key | `your_api_key_here` |
| `JELLYFIN_USER_ID` | Jellyfin user ID | `your_user_id_here` |
| `DISCORD_WEBHOOK_URL` | Default Discord webhook | `https://discord.com/api/webhooks/...` |

### Optional Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DISCORD_WEBHOOK_URL_MOVIES` | Movies-specific webhook | - |
| `DISCORD_WEBHOOK_URL_TV` | TV shows webhook | - |
| `DISCORD_WEBHOOK_URL_MUSIC` | Music webhook | - |
| `OMDB_API_KEY` | OMDb API key for ratings | - |
| `TMDB_API_KEY` | TMDb API key for metadata | - |
| `TVDB_API_KEY` | TVDb API key for TV data | - |
| `LOG_LEVEL` | Logging level | `INFO` |
| `TZ` | Timezone | `UTC` |

## 📊 Supported Architectures

- `linux/amd64` - x86-64
- `linux/arm64` - ARM64 (Raspberry Pi 4, Apple Silicon, etc.)

## 🔗 Ports

| Port | Description |
|------|-------------|
| `1984` | Main webhook service |
| `1985` | Web management interface |

## 📁 Volume Mounts

| Path | Description |
|------|-------------|
| `/app/config` | Configuration files |
| `/app/data` | Database and application data |
| `/app/logs` | Log files |
| `/app/templates` | Jinja2 templates for customization |

## 🚀 Available Tags

| Tag | Description |
|-----|-------------|
| `latest` | Latest stable release |
| `dev` | Development branch |
| `v1.0.0` | Specific version |

## 🔄 Setup Steps

### 1. Create Directories

```bash
mkdir -p jellynouncer/{config,data,logs,templates}
cd jellynouncer
```

### 2. Get API Keys

**Jellyfin API Key:**
1. Go to Jellyfin Dashboard → API Keys
2. Create new key named "Jellynouncer"

**Discord Webhook:**
1. Right-click Discord channel → Edit Channel → Integrations → Webhooks
2. Create new webhook named "Jellynouncer"

### 3. Configure Jellyfin Webhook Plugin

1. Install [Jellyfin Webhook Plugin](https://github.com/jellyfin/jellyfin-plugin-webhook)
2. Add webhook URL: `http://your-server:1984/webhook`
3. Enable "Item Added" and "Item Deleted" events
4. Check "Send All Properties"

## 🔍 Health Check

The container includes built-in health checks:

```bash
# Check container health
docker ps

# Manual health check
curl http://localhost:1984/health
```

## 📋 Examples

### Multi-Channel Setup

```yaml
environment:
  - DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/general
  - DISCORD_WEBHOOK_URL_MOVIES=https://discord.com/api/webhooks/movies
  - DISCORD_WEBHOOK_URL_TV=https://discord.com/api/webhooks/tv
```

### With External APIs

```yaml
environment:
  - OMDB_API_KEY=your_omdb_key
  - TMDB_API_KEY=your_tmdb_key
  - TVDB_API_KEY=your_tvdb_key
```

## 🐛 Troubleshooting

### No Notifications

1. Check webhook URL configuration
2. Verify Jellyfin plugin settings
3. Check logs: `docker logs jellynouncer`

### Permission Issues

```bash
sudo chown -R 1000:1000 jellynouncer/
```

### Reset Database

```bash
rm jellynouncer/data/jellynouncer.db
docker restart jellynouncer
```

## 📚 Links

- **Documentation**: [GitHub Wiki](https://github.com/MarkusMcNugen/Jellynouncer/wiki)
- **Source Code**: [GitHub Repository](https://github.com/MarkusMcNugen/Jellynouncer)
- **Issues**: [Bug Reports](https://github.com/MarkusMcNugen/Jellynouncer/issues)
- **Discussions**: [Community Support](https://github.com/MarkusMcNugen/Jellynouncer/discussions)

## 🤝 Support

If you find this project useful, please consider:
- ⭐ Starring the [GitHub repository](https://github.com/MarkusMcNugen/Jellynouncer)
- 🐛 Reporting issues on [GitHub](https://github.com/MarkusMcNugen/Jellynouncer/issues)
- 💬 Joining discussions on [GitHub](https://github.com/MarkusMcNugen/Jellynouncer/discussions)

---

**Made with ☕ by Mark Newton**