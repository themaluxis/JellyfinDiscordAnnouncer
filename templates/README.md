# Jellynouncer Templates

This directory contains Jinja2 templates for customizing Discord embed notifications.

## Template Types

### Individual Notifications
- `new_item.j2` - Template for new item notifications
- `upgraded_item.j2` - Template for quality upgrade notifications  
- `deleted_item.j2` - Template for deletion notifications

### Grouped Notifications
- `new_items_grouped.j2` - Template for grouped new item notifications
- `upgraded_items_grouped.j2` - Template for grouped upgrade notifications
- `new_items_by_type.j2` - Template for items grouped by content type
- `new_items_by_event.j2` - Template for items grouped by event type

## Available Variables

### Item Properties
- `item.name` - Item name
- `item.type` - Content type (Movie, Series, Episode, Audio, etc.)
- `item.year` - Release year
- `item.overview` - Plot summary/description
- `item.genres` - List of genres
- `item.runtime_ticks` - Runtime in Jellyfin ticks
- `item.resolution` - Video resolution (1080p, 4K, etc.)
- `item.video_codec` - Video codec (H264, H265, etc.)
- `item.audio_codec` - Audio codec (AAC, DTS, etc.)
- `item.audio_channels` - Audio channel configuration (Stereo, 5.1, 7.1)
- `item.has_hdr` - Boolean indicating HDR support
- `item.size` - File size in bytes

### Series/Episode Specific
- `item.series_name` - Series name (for episodes)
- `item.season_number` - Season number
- `item.episode_number` - Episode number

### External Metadata
- `metadata.imdb_rating` - IMDb rating
- `metadata.tmdb_rating` - TMDb rating
- `metadata.poster_url` - Poster image URL
- `metadata.rotten_tomatoes` - Rotten Tomatoes score

### Change Detection (Upgrade Templates)
- `changes` - Dictionary of detected changes
- `changes.resolution` - Resolution change details
- `changes.video_codec` - Video codec change details
- `changes.audio_codec` - Audio codec change details
- `changes.hdr` - HDR status change details

## Custom Filters

### Text Formatting
- `truncate_text(max_length)` - Truncate text to specified length
- `join_with_limit(separator, max_length)` - Join list items with length limit

### Time/Date Formatting
- `format_runtime` - Convert runtime ticks to human readable format
- `discord_timestamp(format)` - Convert ISO timestamp to Discord format

### File Size
- `format_file_size` - Format bytes to human readable size

## Functions
- `now()` - Current datetime
- `format_change(change)` - Format a change object for display

## Discord Embed Limits

When creating templates, keep Discord's embed limits in mind:
- Title: 256 characters
- Description: 4096 characters  
- Field name: 256 characters
- Field value: 1024 characters
- Footer text: 2048 characters
- Total embed: 6000 characters
- Fields per embed: 25

## Color Values

Common color values for Discord embeds:
- Jellyfin Green: `6736947` (`0x66BB6A`)
- Discord Blue: `5793266` (`0x5865F2`) 
- Success Green: `3066993` (`0x2ECC71`)
- Warning Yellow: `16776960` (`0xFFD700`)
- Error Red: `15158332` (`0xE74C3C`)
- Info Blue: `3447003` (`0x3498DB`)

## Template Validation

Templates are automatically validated when:
- The service starts up
- Templates are modified via the web interface
- The `/validate-templates` endpoint is called

Invalid templates will fall back to built-in defaults and log errors.