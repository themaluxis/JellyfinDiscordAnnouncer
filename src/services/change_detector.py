"""
Change detection system for identifying quality upgrades and significant changes.
"""

import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

from src.services.jellyfin_api import MediaItem


@dataclass
class DetectedChange:
    """Represents a detected change in media quality."""
    change_type: str  # resolution, codec, audio_codec, hdr, channels
    old_value: Optional[str]
    new_value: Optional[str]
    is_upgrade: bool
    
    def __str__(self):
        direction = "upgraded" if self.is_upgrade else "changed"
        return f"{self.change_type} {direction} from {self.old_value} to {self.new_value}"


class ChangeDetector:
    """Detects and analyzes changes between media items."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Quality hierarchies for upgrade detection
        self.resolution_hierarchy = ["480p", "720p", "1080p", "4K", "8K"]
        self.codec_hierarchy = ["MPEG2", "H264", "H265", "AV1"]
        self.audio_codec_hierarchy = ["MP3", "AAC", "AC3", "DTS", "TRUEHD", "ATMOS"]
        self.channel_hierarchy = ["Mono", "Stereo", "5.1", "7.1"]
    
    def detect_changes(self, old_item: MediaItem, new_item: MediaItem) -> Dict[str, DetectedChange]:
        """
        Detect changes between two media items.
        
        Args:
            old_item: Previous version of the item
            new_item: New version of the item
            
        Returns:
            Dictionary of detected changes by change type
        """
        changes = {}
        
        # Check resolution changes
        old_resolution = old_item.resolution
        new_resolution = new_item.resolution
        if old_resolution != new_resolution:
            change = DetectedChange(
                change_type="resolution",
                old_value=old_resolution,
                new_value=new_resolution,
                is_upgrade=self._is_resolution_upgrade(old_resolution, new_resolution)
            )
            changes["resolution"] = change
            self.logger.debug(f"Resolution change detected: {change}")
        
        # Check video codec changes
        old_codec = old_item.video_codec
        new_codec = new_item.video_codec
        if old_codec != new_codec:
            change = DetectedChange(
                change_type="video_codec",
                old_value=old_codec,
                new_value=new_codec,
                is_upgrade=self._is_codec_upgrade(old_codec, new_codec)
            )
            changes["video_codec"] = change
            self.logger.debug(f"Video codec change detected: {change}")
        
        # Check audio codec changes
        old_audio = old_item.audio_codec
        new_audio = new_item.audio_codec
        if old_audio != new_audio:
            change = DetectedChange(
                change_type="audio_codec",
                old_value=old_audio,
                new_value=new_audio,
                is_upgrade=self._is_audio_codec_upgrade(old_audio, new_audio)
            )
            changes["audio_codec"] = change
            self.logger.debug(f"Audio codec change detected: {change}")
        
        # Check HDR changes
        old_hdr = old_item.has_hdr
        new_hdr = new_item.has_hdr
        if old_hdr != new_hdr:
            change = DetectedChange(
                change_type="hdr",
                old_value="HDR" if old_hdr else "SDR",
                new_value="HDR" if new_hdr else "SDR",
                is_upgrade=new_hdr and not old_hdr  # Only upgrade if adding HDR
            )
            changes["hdr"] = change
            self.logger.debug(f"HDR change detected: {change}")
        
        # Check audio channel changes
        old_channels = old_item.audio_channels
        new_channels = new_item.audio_channels
        if old_channels != new_channels:
            change = DetectedChange(
                change_type="audio_channels",
                old_value=old_channels,
                new_value=new_channels,
                is_upgrade=self._is_channel_upgrade(old_channels, new_channels)
            )
            changes["audio_channels"] = change
            self.logger.debug(f"Audio channel change detected: {change}")
        
        # Check file size changes (significant increases might indicate quality upgrade)
        if old_item.size and new_item.size:
            size_increase_percent = ((new_item.size - old_item.size) / old_item.size) * 100
            if size_increase_percent > 50:  # 50% size increase threshold
                change = DetectedChange(
                    change_type="file_size",
                    old_value=self._format_file_size(old_item.size),
                    new_value=self._format_file_size(new_item.size),
                    is_upgrade=True
                )
                changes["file_size"] = change
                self.logger.debug(f"Significant file size increase detected: {change}")
        
        if changes:
            upgrade_count = sum(1 for change in changes.values() if change.is_upgrade)
            self.logger.info(f"Detected {len(changes)} changes for {new_item.name}, {upgrade_count} are upgrades")
        
        return changes
    
    def _is_resolution_upgrade(self, old_res: Optional[str], new_res: Optional[str]) -> bool:
        """Check if resolution change is an upgrade."""
        if not old_res or not new_res:
            return False
        
        try:
            old_index = self.resolution_hierarchy.index(old_res)
            new_index = self.resolution_hierarchy.index(new_res)
            return new_index > old_index
        except ValueError:
            # Handle custom resolutions by comparing pixel counts
            return self._compare_custom_resolutions(old_res, new_res)
    
    def _is_codec_upgrade(self, old_codec: Optional[str], new_codec: Optional[str]) -> bool:
        """Check if video codec change is an upgrade."""
        if not old_codec or not new_codec:
            return False
        
        # Normalize codec names
        old_normalized = self._normalize_codec_name(old_codec)
        new_normalized = self._normalize_codec_name(new_codec)
        
        try:
            old_index = self.codec_hierarchy.index(old_normalized)
            new_index = self.codec_hierarchy.index(new_normalized)
            return new_index > old_index
        except ValueError:
            # If codec not in hierarchy, assume it's an upgrade if different
            return old_normalized != new_normalized
    
    def _is_audio_codec_upgrade(self, old_codec: Optional[str], new_codec: Optional[str]) -> bool:
        """Check if audio codec change is an upgrade."""
        if not old_codec or not new_codec:
            return False
        
        old_normalized = old_codec.upper()
        new_normalized = new_codec.upper()
        
        try:
            old_index = self.audio_codec_hierarchy.index(old_normalized)
            new_index = self.audio_codec_hierarchy.index(new_normalized)
            return new_index > old_index
        except ValueError:
            return old_normalized != new_normalized
    
    def _is_channel_upgrade(self, old_channels: Optional[str], new_channels: Optional[str]) -> bool:
        """Check if audio channel change is an upgrade."""
        if not old_channels or not new_channels:
            return False
        
        try:
            old_index = self.channel_hierarchy.index(old_channels)
            new_index = self.channel_hierarchy.index(new_channels)
            return new_index > old_index
        except ValueError:
            return False
    
    def _normalize_codec_name(self, codec: str) -> str:
        """Normalize codec name for comparison."""
        codec_upper = codec.upper()
        
        # Common codec mappings
        if "H264" in codec_upper or "AVC" in codec_upper:
            return "H264"
        elif "H265" in codec_upper or "HEVC" in codec_upper:
            return "H265"
        elif "AV1" in codec_upper:
            return "AV1"
        elif "MPEG2" in codec_upper:
            return "MPEG2"
        
        return codec_upper
    
    def _compare_custom_resolutions(self, old_res: str, new_res: str) -> bool:
        """Compare custom resolution strings by extracting pixel counts."""
        try:
            # Extract width from resolution strings like "1920x1080"
            old_width = int(old_res.split('x')[0]) if 'x' in old_res else 0
            new_width = int(new_res.split('x')[0]) if 'x' in new_res else 0
            
            return new_width > old_width
        except (ValueError, IndexError):
            return False
    
    def _format_file_size(self, size_bytes: int) -> str:
        """Format file size in human-readable format."""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} PB"
    
    def is_significant_change(self, changes: Dict[str, DetectedChange]) -> bool:
        """
        Determine if changes are significant enough to warrant notification.
        
        Args:
            changes: Dictionary of detected changes
            
        Returns:
            True if changes are significant
        """
        if not changes:
            return False
        
        # Any upgrade is considered significant
        if any(change.is_upgrade for change in changes.values()):
            return True
        
        # Multiple changes might be significant even if not upgrades
        if len(changes) >= 3:
            return True
        
        # HDR addition is always significant
        if "hdr" in changes and changes["hdr"].new_value == "HDR":
            return True
        
        return False
    
    def get_change_summary(self, changes: Dict[str, DetectedChange]) -> str:
        """
        Get a human-readable summary of changes.
        
        Args:
            changes: Dictionary of detected changes
            
        Returns:
            Summary string
        """
        if not changes:
            return "No significant changes detected"
        
        upgrades = [change for change in changes.values() if change.is_upgrade]
        other_changes = [change for change in changes.values() if not change.is_upgrade]
        
        summary_parts = []
        
        if upgrades:
            upgrade_descriptions = [str(change) for change in upgrades]
            summary_parts.append(f"Upgrades: {', '.join(upgrade_descriptions)}")
        
        if other_changes:
            change_descriptions = [str(change) for change in other_changes]
            summary_parts.append(f"Changes: {', '.join(change_descriptions)}")
        
        return "; ".join(summary_parts)