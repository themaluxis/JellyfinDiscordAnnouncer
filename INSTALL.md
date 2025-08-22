# Jellynouncer Installation Guide

This guide will help you install and configure Jellynouncer for your Jellyfin media server.

## Prerequisites

Before installing Jellynouncer, ensure you have:

1. **Jellyfin Server 10.8+** with the [Webhook Plugin](https://github.com/jellyfin/jellyfin-plugin-webhook) installed
2. **Discord Server** with webhook creation permissions
3. **Docker** (recommended) or **Python 3.13+** for manual installation

## Quick Start with Docker

### 1. Download Files

```bash
mkdir jellynouncer && cd jellynouncer
wget https://raw.githubusercontent.com/MarkusMcNugen/Jellynouncer/main/docker-compose.yml
wget https://raw.githubusercontent.com/MarkusMcNugen/Jellynouncer/main/.env.example
```

### 2. Configure Environment

```bash
cp .env.example .env
```

Edit `.env` with your configuration:

```bash
# Required settings
JELLYFIN_SERVER_URL=http://your-jellyfin-server:8096
JELLYFIN_API_KEY=your_api_key_here
JELLYFIN_USER_ID=your_user_id_here
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/your/webhook
```

### 3. Create Directories

```bash
mkdir -p config data logs templates
```

### 4. Start Service

```bash
docker-compose up -d
```

### 5. Configure Jellyfin Webhook

1. Go to Jellyfin Dashboard → Plugins → Webhook
2. Add new webhook: `http://your-server:1984/webhook`
3. Enable "Item Added" and "Item Deleted" events
4. Check "Send All Properties"
5. Save configuration

## Getting API Keys

### Jellyfin API Key

1. Go to Jellyfin Dashboard → API Keys
2. Click "+" to create new API key
3. Name it "Jellynouncer"
4. Copy the generated key

### Jellyfin User ID

1. Go to Jellyfin Dashboard → Users
2. Click on your admin user
3. Copy the ID from the URL: `/web/index.html#!/users/user?userId=USER_ID_HERE`

### Discord Webhook URL

1. Go to your Discord server
2. Right-click the channel → Edit Channel → Integrations → Webhooks
3. Click "New Webhook"
4. Name it "Jellynouncer"
5. Copy the webhook URL

### Optional: External API Keys

For enhanced metadata and posters:

- **OMDb**: Get free key at [omdbapi.com](http://omdbapi.com/apikey.aspx)
- **TMDb**: Get free key at [themoviedb.org/settings/api](https://www.themoviedb.org/settings/api)
- **TVDb**: Get key at [thetvdb.com/api-information](https://thetvdb.com/api-information)

## Manual Installation

### 1. Clone Repository

```bash
git clone https://github.com/MarkusMcNugen/Jellynouncer.git
cd Jellynouncer
```

### 2. Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Build Web Interface

```bash
cd web
npm install
npm run build
cd ..
```

### 5. Configure

```bash
cp config/config.json.example config/config.json
# Edit config.json with your settings
```

### 6. Run

```bash
python main.py
```

## Configuration Options

### Grouping Modes

Configure how notifications are batched:

- `none` - Send immediately
- `event` - Group by event type (new vs upgrade)
- `type` - Group by content type (movies vs TV)
- `both` - Group by both event and content type

### Change Detection

Control which quality changes trigger notifications:

```json
{
  "notifications": {
    "watch_changes": {
      "resolution": true,      // 1080p → 4K
      "codec": true,           // H264 → H265
      "audio_codec": true,     // AAC → DTS
      "hdr_status": true,      // SDR → HDR
      "quality": true,         // Overall quality improvements
      "file_size": false       // Significant file size increases
    }
  }
}
```

### Web Interface

Access the management interface at `http://your-server:1985`

Default features:
- Dashboard with statistics
- Configuration management
- Template editor
- Log viewer
- Health monitoring

## Troubleshooting

### No Notifications Received

1. Check Jellyfin webhook configuration
2. Verify webhook URL: `http://your-server:1984/webhook`
3. Test with `/test-webhook` endpoint
4. Check logs: `docker logs jellynouncer`

### Database Errors

```bash
# Check permissions
ls -la data/

# Reset database (loses history)
rm data/jellynouncer.db
docker restart jellynouncer
```

### High Resource Usage

Reduce grouping settings:
```json
{
  "grouping": {
    "delay_minutes": 10,
    "max_items": 5
  }
}
```

### Template Errors

1. Use the web interface template editor
2. Check template syntax at startup
3. Templates auto-fallback to defaults on errors

## Systemd Service (Linux)

For manual installations, create `/etc/systemd/system/jellynouncer.service`:

```ini
[Unit]
Description=Jellynouncer Discord Webhook Service
After=network.target

[Service]
Type=simple
User=jellynouncer
WorkingDirectory=/opt/jellynouncer
Environment="PATH=/opt/jellynouncer/venv/bin"
ExecStart=/opt/jellynouncer/venv/bin/python main.py
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable jellynouncer
sudo systemctl start jellynouncer
```

## Performance Tuning

### For Large Libraries (10,000+ items)

```json
{
  "system": {
    "max_workers": 8,
    "batch_size": 100
  },
  "discord": {
    "webhooks": {
      "default": {
        "grouping": {
          "delay_minutes": 15,
          "max_items": 50
        }
      }
    }
  }
}
```

### For High-Frequency Updates

Enable aggressive filtering:
```json
{
  "notifications": {
    "filter_renames": true,
    "filter_deletes": true,
    "deletion_delay_seconds": 60,
    "minimum_file_size_mb": 100
  }
}
```

## Security

### Network Security

- Run behind reverse proxy with SSL
- Use firewall rules to restrict access
- Set strong JWT secret for web interface

### Data Protection

- Regularly backup `data/` directory
- Monitor log files for errors
- Keep API keys secure and rotate regularly

## Support

- **Issues**: [GitHub Issues](https://github.com/MarkusMcNugen/Jellynouncer/issues)
- **Discussions**: [GitHub Discussions](https://github.com/MarkusMcNugen/Jellynouncer/discussions)
- **Wiki**: [GitHub Wiki](https://github.com/MarkusMcNugen/Jellynouncer/wiki)