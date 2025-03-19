"""Delta update module for PyAutoUpdater.

This module provides incremental update functionality for more efficient updates
by only downloading and applying changes between versions.
"""

import os
import logging
import hashlib
import json
from typing import Dict, List, Tuple, Optional, Any, Set
from pathlib import Path

logger = logging.getLogger(__name__)


class DeltaManager:
    """Manages delta (incremental) updates."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the delta manager.

        Args:
            config: Optional configuration dictionary with the following keys:
                - enable_delta: Whether to enable delta updates (default: True)
                - manifest_filename: Filename for the manifest file (default: 'manifest.json')
                - chunk_size: Chunk size for file hashing (default: 4096)
        """
        self.config = config or {}
        self.enable_delta = self.config.get('enable_delta', True)
        self.manifest_filename = self.config.get('manifest_filename', 'manifest.json')
        self.chunk_size = self.config.get('chunk_size', 4096)

    def generate_manifest(self, directory: str) -> Dict[str, Any]:
        """Generate a manifest file for the given directory.

        Args:
            directory: Directory to generate manifest for

        Returns:
            Manifest dictionary with file information
        """
        manifest = {
            'files': {},
            'version': '1.0',
            'timestamp': os.path.getmtime(directory)
        }

        for root, _, files in os.walk(directory):
            for file in files:
                # Skip the manifest file itself
                if file == self.manifest_filename:
                    continue

                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, directory)

                # Calculate file hash and size
                file_hash = self._calculate_file_hash(file_path)
                file_size = os.path.getsize(file_path)
                file_time = os.path.getmtime(file_path)

                manifest['files'][rel_path] = {
                    'hash': file_hash,
                    'size': file_size,
                    'modified': file_time
                }

        return manifest

    def save_manifest(self, directory: str, manifest: Dict[str, Any]) -> str:
        """Save a manifest to a file.

        Args:
            directory: Directory to save the manifest in
            manifest: Manifest dictionary

        Returns:
            Path to the saved manifest file
        """
        manifest_path = os.path.join(directory, self.manifest_filename)
        with open(manifest_path, 'w') as f:
            json.dump(manifest, f, indent=2)
        return manifest_path

    def load_manifest(self, manifest_path: str) -> Optional[Dict[str, Any]]:
        """Load a manifest from a file.

        Args:
            manifest_path: Path to the manifest file

        Returns:
            Manifest dictionary or None if loading failed
        """
        try:
            with open(manifest_path, 'r') as f:
                return json.load(f)
        except (IOError, json.JSONDecodeError) as e:
            logger.error(f"Failed to load manifest: {str(e)}")
            return None

    def compare_manifests(self, old_manifest: Dict[str, Any], new_manifest: Dict[str, Any]) -> Dict[str, List[str]]:
        """Compare two manifests to determine changes.

        Args:
            old_manifest: Old manifest dictionary
            new_manifest: New manifest dictionary

        Returns:
            Dictionary with lists of added, modified, and removed files
        """
        old_files = set(old_manifest.get('files', {}).keys())
        new_files = set(new_manifest.get('files', {}).keys())

        # Files that exist in both manifests
        common_files = old_files.intersection(new_files)

        # Find modified files by comparing hashes
        modified_files = []
        for file in common_files:
            old_hash = old_manifest['files'][file].get('hash')
            new_hash = new_manifest['files'][file].get('hash')
            if old_hash != new_hash:
                modified_files.append(file)

        # Files that exist only in the new manifest (added)
        added_files = list(new_files - old_files)

        # Files that exist only in the old manifest (removed)
        removed_files = list(old_files - new_files)

        return {
            'added': added_files,
            'modified': modified_files,
            'removed': removed_files
        }

    def get_delta_update_files(self, source_dir: str, target_dir: str) -> Dict[str, List[str]]:
        """Get the list of files that need to be updated based on delta comparison.

        Args:
            source_dir: Source directory (current version)
            target_dir: Target directory (new version)

        Returns:
            Dictionary with lists of files to add, modify, and remove
        """
        if not self.enable_delta:
            # If delta updates are disabled, return all files in target_dir as 'added'
            all_files = []
            for root, _, files in os.walk(target_dir):
                for file in files:
                    if file == self.manifest_filename:
                        continue
                    file_path = os.path.join(root, file)
                    rel_path = os.path.relpath(file_path, target_dir)
                    all_files.append(rel_path)
            return {'added': all_files, 'modified': [], 'removed': []}

        # Generate manifests for both directories
        source_manifest = self.generate_manifest(source_dir)
        target_manifest = self.generate_manifest(target_dir)

        # Compare manifests
        return self.compare_manifests(source_manifest, target_manifest)

    def apply_delta_update(self, source_dir: str, update_dir: str, changes: Dict[str, List[str]]) -> bool:
        """Apply a delta update to the source directory.

        Args:
            source_dir: Source directory to update
            update_dir: Directory containing update files
            changes: Dictionary with lists of files to add, modify, and remove

        Returns:
            True if update succeeded, False otherwise
        """
        try:
            # Remove files that are no longer needed
            for file in changes.get('removed', []):
                file_path = os.path.join(source_dir, file)
                if os.path.exists(file_path):
                    os.remove(file_path)
                    logger.debug(f"Removed file: {file}")

            # Add or modify files
            for file_list in [changes.get('added', []), changes.get('modified', [])]:
                for file in file_list:
                    src_path = os.path.join(update_dir, file)
                    dst_path = os.path.join(source_dir, file)

                    # Create directory if it doesn't exist
                    os.makedirs(os.path.dirname(dst_path), exist_ok=True)

                    # Copy the file
                    with open(src_path, 'rb') as src_file, open(dst_path, 'wb') as dst_file:
                        dst_file.write(src_file.read())
                    logger.debug(f"Updated file: {file}")

            return True
        except Exception as e:
            logger.exception(f"Failed to apply delta update: {str(e)}")
            return False

    def _calculate_file_hash(self, file_path: str) -> str:
        """Calculate the SHA-256 hash of a file.

        Args:
            file_path: Path to the file

        Returns:
            SHA-256 hash as a hexadecimal string
        """
        sha256_hash = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(self.chunk_size), b""):
                sha256_hash.update(chunk)
        return sha256_hash.hexdigest()


# Utility functions for binary diff and patch
try:
    import bsdiff4
    BSDIFF_AVAILABLE = True
except ImportError:
    BSDIFF_AVAILABLE = False


def create_binary_diff(old_file: str, new_file: str, diff_file: str) -> bool:
    """Create a binary diff between two files using bsdiff4.

    Args:
        old_file: Path to the old file
        new_file: Path to the new file
        diff_file: Path to save the diff file

    Returns:
        True if diff creation succeeded, False otherwise
    """
    if not BSDIFF_AVAILABLE:
        logger.error("bsdiff4 library not available for binary diff")
        return False

    try:
        bsdiff4.file_diff(old_file, new_file, diff_file)
        return True
    except Exception as e:
        logger.exception(f"Failed to create binary diff: {str(e)}")
        return False


def apply_binary_patch(old_file: str, new_file: str, patch_file: str) -> bool:
    """Apply a binary patch to a file using bsdiff4.

    Args:
        old_file: Path to the old file
        new_file: Path to save the new file
        patch_file: Path to the patch file

    Returns:
        True if patch application succeeded, False otherwise
    """
    if not BSDIFF_AVAILABLE:
        logger.error("bsdiff4 library not available for binary patch")
        return False

    try:
        bsdiff4.file_patch(old_file, new_file, patch_file)
        return True
    except Exception as e:
        logger.exception(f"Failed to apply binary patch: {str(e)}")
        return False