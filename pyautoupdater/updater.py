"""Update process module for PyAutoUpdater.

This module handles the actual update process, including download management,
file operations, and update verification.
"""

import os
import sys
import shutil
import tempfile
import logging
import hashlib
import subprocess
import platform
import time
from typing import Dict, List, Optional, Callable, Tuple, Any, Union
import requests
from pathlib import Path
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor

from .version import VersionManager
from .hooks import HookManager
from .security import SecurityManager
from .packagers import PackageAdapter
from .delta import DeltaManager

logger = logging.getLogger(__name__)


class UpdateManager:
    """Manages the update process for the application."""

    def __init__(self, 
                 config: Dict[str, Any],
                 hook_manager: Optional[HookManager] = None,
                 security_manager: Optional[SecurityManager] = None,
                 delta_manager: Optional[DeltaManager] = None):
        """Initialize the update manager.

        Args:
            config: Configuration dictionary with the following keys:
                - package_name: Name of the package
                - current_version: Current version of the package
                - repositories: List of repository configurations
                - temp_dir: Optional temporary directory for downloads
                - backup_dir: Optional backup directory for rollback
                - max_download_retries: Maximum number of download retries
                - chunk_size: Chunk size for downloads
                - timeout: Timeout for network operations
                - proxy: Optional proxy configuration
                - enable_delta: Whether to enable delta updates
                - security: Security configuration options
            hook_manager: Optional hook manager for lifecycle hooks
            security_manager: Optional security manager for verification
            delta_manager: Optional delta manager for incremental updates
        """
        self.config = config
        self.package_name = config['package_name']
        self.current_version = config['current_version']
        self.repositories = config['repositories']
        self.temp_dir = config.get('temp_dir', tempfile.gettempdir())
        self.backup_dir = config.get('backup_dir', os.path.join(self.temp_dir, 'backup'))
        self.max_retries = config.get('max_download_retries', 3)
        self.chunk_size = config.get('chunk_size', 8192)  # 8KB chunks
        self.timeout = config.get('timeout', 30)  # 30 seconds
        self.proxy = config.get('proxy', None)
        self.enable_delta = config.get('enable_delta', True)
        
        # Create version manager
        self.version_manager = VersionManager(
            self.package_name,
            self.current_version,
            self.repositories
        )
        
        # Use provided managers or create new ones
        self.hook_manager = hook_manager or HookManager()
        self.security_manager = security_manager or SecurityManager(config.get('security', {}))
        self.delta_manager = delta_manager or DeltaManager(config.get('delta', {}))
        
        # State tracking
        self._update_in_progress = False
        self._download_progress_callback = None
        self._status_callback = None

    def check_for_updates(self) -> Tuple[bool, Optional[str], Optional[Dict]]:
        """Check if updates are available.

        Returns:
            Tuple containing:
                - Boolean indicating if an update is available
                - Latest version string if update is available, None otherwise
                - Version info dictionary if update is available, None otherwise
        """
        return self.version_manager.check_update()

    def perform_update(self, 
                      progress_callback: Optional[Callable[[float, str], None]] = None,
                      status_callback: Optional[Callable[[str, Dict], None]] = None) -> bool:
        """Perform the update process.

        Args:
            progress_callback: Optional callback for progress updates
            status_callback: Optional callback for status updates

        Returns:
            True if update was successful, False otherwise
        """
        if self._update_in_progress:
            logger.warning("Update already in progress")
            return False

        self._update_in_progress = True
        self._download_progress_callback = progress_callback
        self._status_callback = status_callback

        try:
            # Check for updates
            update_available, latest_version, version_info = self.check_for_updates()
            if not update_available:
                self._update_status("No updates available", {'current_version': self.current_version})
                return False

            self._update_status("Update available", {
                'current_version': self.current_version,
                'latest_version': latest_version,
                'version_info': version_info
            })

            # Run pre-update hooks
            if not self._run_pre_update_hooks(version_info):
                self._update_status("Pre-update hooks failed", {'version': latest_version})
                return False

            # Download the update
            download_path = self._download_update(version_info)
            if not download_path:
                self._update_status("Download failed", {'version': latest_version})
                return False

            # Verify the update
            if not self._verify_update(download_path, version_info):
                self._update_status("Verification failed", {'version': latest_version})
                return False

            # Create backup
            if not self._create_backup():
                self._update_status("Backup failed", {'version': latest_version})
                return False

            # Install the update
            if not self._install_update(download_path, version_info):
                self._update_status("Installation failed", {'version': latest_version})
                self._restore_backup()
                return False

            # Run post-update hooks
            if not self._run_post_update_hooks(version_info):
                self._update_status("Post-update hooks failed", {'version': latest_version})
                self._restore_backup()
                return False

            # Clean up
            self._cleanup(download_path)

            self._update_status("Update successful", {
                'previous_version': self.current_version,
                'new_version': latest_version
            })
            return True

        except Exception as e:
            logger.exception(f"Update failed: {str(e)}")
            self._update_status("Update failed", {'error': str(e)})
            self._restore_backup()
            return False
        finally:
            self._update_in_progress = False

    def _update_status(self, status: str, data: Dict[str, Any]) -> None:
        """Update the status and call the status callback if provided.

        Args:
            status: Status message
            data: Status data dictionary
        """
        logger.info(f"Update status: {status}")
        if self._status_callback:
            try:
                self._status_callback(status, data)
            except Exception as e:
                logger.error(f"Error in status callback: {str(e)}")

    def _update_progress(self, progress: float, message: str) -> None:
        """Update the progress and call the progress callback if provided.

        Args:
            progress: Progress value between 0 and 1
            message: Progress message
        """
        logger.debug(f"Update progress: {progress:.2f} - {message}")
        if self._download_progress_callback:
            try:
                self._download_progress_callback(progress, message)
            except Exception as e:
                logger.error(f"Error in progress callback: {str(e)}")

    def _run_pre_update_hooks(self, version_info: Dict) -> bool:
        """Run pre-update hooks.

        Args:
            version_info: Version information dictionary

        Returns:
            True if all hooks succeeded, False otherwise
        """
        self._update_status("Running pre-update hooks", {'version_info': version_info})
        return self.hook_manager.run_pre_update_hooks(version_info)

    def _run_post_update_hooks(self, version_info: Dict) -> bool:
        """Run post-update hooks.

        Args:
            version_info: Version information dictionary

        Returns:
            True if all hooks succeeded, False otherwise
        """
        self._update_status("Running post-update hooks", {'version_info': version_info})
        return self.hook_manager.run_post_update_hooks(version_info)

    def _download_update(self, version_info: Dict) -> Optional[str]:
        """Download the update package.

        Args:
            version_info: Version information dictionary

        Returns:
            Path to the downloaded file or None if download failed
        """
        download_url = version_info.get('download_url')
        if not download_url:
            logger.error("No download URL found in version info")
            return None

        # Create temp directory if it doesn't exist
        os.makedirs(self.temp_dir, exist_ok=True)

        # Parse filename from URL
        parsed_url = urlparse(download_url)
        filename = os.path.basename(parsed_url.path)
        download_path = os.path.join(self.temp_dir, filename)

        self._update_status("Downloading update", {
            'url': download_url,
            'destination': download_path
        })

        # Set up proxy if configured
        proxies = None
        if self.proxy:
            proxies = {
                'http': self.proxy,
                'https': self.proxy
            }

        # Download with retry logic
        for attempt in range(1, self.max_retries + 1):
            try:
                # Check if file exists and get its size for resume
                file_size = 0
                headers = {}
                if os.path.exists(download_path):
                    file_size = os.path.getsize(download_path)
                    if file_size > 0:
                        headers['Range'] = f'bytes={file_size}-'

                # Make request with proper headers for resume
                response = requests.get(
                    download_url,
                    headers=headers,
                    stream=True,
                    timeout=self.timeout,
                    proxies=proxies,
                    verify=True  # Always verify SSL
                )
                response.raise_for_status()

                # Get total file size
                total_size = int(response.headers.get('content-length', 0))
                if 'content-range' in response.headers:
                    content_range = response.headers['content-range']
                    total_size = int(content_range.split('/')[-1])

                # If we already have the complete file, return the path
                if file_size == total_size and total_size > 0:
                    logger.info("File already completely downloaded")
                    return download_path

                # Open file in append mode if resuming, otherwise write mode
                mode = 'ab' if file_size > 0 and total_size > file_size else 'wb'
                with open(download_path, mode) as f:
                    downloaded = file_size
                    for chunk in response.iter_content(chunk_size=self.chunk_size):
                        if chunk:  # Filter out keep-alive chunks
                            f.write(chunk)
                            downloaded += len(chunk)
                            progress = downloaded / total_size if total_size > 0 else 0
                            self._update_progress(
                                progress,
                                f"Downloaded {downloaded} / {total_size} bytes"
                            )

                logger.info(f"Download completed: {download_path}")
                return download_path

            except (requests.RequestException, IOError) as e:
                logger.warning(f"Download attempt {attempt} failed: {str(e)}")
                if attempt < self.max_retries:
                    # Exponential backoff
                    wait_time = 2 ** (attempt - 1)
                    logger.info(f"Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    logger.error("Maximum retry attempts reached")
                    return None

        return None

    def _verify_update(self, download_path: str, version_info: Dict) -> bool:
        """Verify the downloaded update package.

        Args:
            download_path: Path to the downloaded file
            version_info: Version information dictionary

        Returns:
            True if verification succeeded, False otherwise
        """
        self._update_status("Verifying update package", {'path': download_path})

        # Check if file exists
        if not os.path.exists(download_path):
            logger.error(f"Downloaded file not found: {download_path}")
            return False

        # Verify SHA256 checksum if available
        expected_sha256 = version_info.get('sha256')
        if expected_sha256:
            sha256 = self._calculate_sha256(download_path)
            if sha256 != expected_sha256:
                logger.error(f"SHA256 verification failed. Expected: {expected_sha256}, Got: {sha256}")
                return False
            logger.info("SHA256 verification passed")

        # Verify digital signature if security manager is available
        if self.security_manager and hasattr(self.security_manager, 'verify_signature'):
            if not self.security_manager.verify_signature(download_path, version_info):
                logger.error("Digital signature verification failed")
                return False
            logger.info("Digital signature verification passed")

        return True

    def _calculate_sha256(self, file_path: str) -> str:
        """Calculate SHA256 hash of a file.

        Args:
            file_path: Path to the file

        Returns:
            SHA256 hash as a hexadecimal string
        """
        sha256_hash = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(self.chunk_size), b""):
                sha256_hash.update(chunk)
        return sha256_hash.hexdigest()

    def _create_backup(self) -> bool:
        """Create a backup of the current installation.

        Returns:
            True if backup succeeded, False otherwise
        """
        self._update_status("Creating backup", {'backup_dir': self.backup_dir})

        try:
            # Determine the application directory
            app_dir = self._get_application_directory()
            if not app_dir:
                logger.error("Could not determine application directory")
                return False

            # Create backup directory if it doesn't exist
            os.makedirs(self.backup_dir, exist_ok=True)

            # Create a timestamped backup directory
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            backup_subdir = os.path.join(self.backup_dir, f"{self.package_name}_{timestamp}")
            os.makedirs(backup_subdir, exist_ok=True)

            # Copy all files from app directory to backup directory
            self._copy_directory(app_dir, backup_subdir)

            # Store backup path for potential rollback
            self._current_backup_path = backup_subdir
            logger.info(f"Backup created at {backup_subdir}")
            return True

        except Exception as e:
            logger.exception(f"Backup creation failed: {str(e)}")
            return False

    def _restore_backup(self) -> bool:
        """Restore from backup if available.

        Returns:
            True if restore succeeded, False otherwise
        """
        if not hasattr(self, '_current_backup_path') or not self._current_backup_path:
            logger.warning("No backup available to restore")
            return False

        self._update_status("Restoring from backup", {'backup_path': self._current_backup_path})

        try:
            # Determine the application directory
            app_dir = self._get_application_directory()
            if not app_dir:
                logger.error("Could not determine application directory")
                return False

            # Copy all files from backup directory to app directory
            self._copy_directory(self._current_backup_path, app_dir)

            logger.info(f"Restored from backup {self._current_backup_path}")
            return True

        except Exception as e:
            logger.exception(f"Backup restoration failed: {str(e)}")
            return False

    def _install_update(self, download_path: str, version_info: Dict) -> bool:
        """Install the update package.

        Args:
            download_path: Path to the downloaded file
            version_info: Version information dictionary

        Returns:
            True if installation succeeded, False otherwise
        """
        self._update_status("Installing update", {'package': download_path})

        try:
            # Determine the application directory
            app_dir = self._get_application_directory()
            if not app_dir:
                logger.error("Could not determine application directory")
                return False

            # Extract the package to a temporary directory
            extract_dir = os.path.join(self.temp_dir, f"extract_{time.time()}")
            os.makedirs(extract_dir, exist_ok=True)

            # Extract based on file type
            if download_path.endswith('.whl'):
                self._extract_wheel(download_path, extract_dir)
            elif download_path.endswith('.tar.gz') or download_path.endswith('.tgz'):
                self._extract_targz(download_path, extract_dir)
            elif download_path.endswith('.zip'):
                self._extract_zip(download_path, extract_dir)
            else:
                logger.error(f"Unsupported package format: {download_path}")
                return False

            # Detect build type (PyInstaller, Nuitka, or hybrid)
            build_type = self._detect_build_type(app_dir)
            logger.info(f"Detected build type: {build_type}")

            # Apply update based on build type
            if build_type == 'pyinstaller':
                success = self._update_pyinstaller(app_dir, extract_dir, version_info)
            elif build_type == 'nuitka':
                success = self._update_nuitka(app_dir, extract_dir, version_info)
            elif build_type == 'hybrid':
                success = self._update_hybrid(app_dir, extract_dir, version_info)
            else:  # 'standard' or unknown
                success = self._update_standard(app_dir, extract_dir, version_info)

            # Clean up extraction directory
            shutil.rmtree(extract_dir, ignore_errors=True)

            if success:
                # Update current version
                self.current_version = version_info.get('version', self.current_version)
                logger.info(f"Update installed successfully, new version: {self.current_version}")
                return True
            else:
                logger.error("Update installation failed")
                return False

        except Exception as e:
            logger.exception(f"Update installation failed: {str(e)}")
            return False

    def _get_application_directory(self) -> Optional[str]:
        """Determine the application directory.

        Returns:
            Application directory path or None if not found
        """
        # Try to get the directory of the main executable
        if getattr(sys, 'frozen', False):
            # PyInstaller creates a temp folder and stores path in _MEIPASS
            if hasattr(sys, '_MEIPASS'):
                return sys._MEIPASS
            # Otherwise, use the executable path
            return os.path.dirname(sys.executable)
        else:
            # For standard Python execution, use the main module directory
            main_module = sys.modules.get('__main__')
            if main_module and hasattr(main_module, '__file__'):
                return os.path.dirname(os.path.abspath(main_module.__file__))

        # Fallback to current working directory
        return os.getcwd()

    def _copy_directory(self, src: str, dst: str) -> None:
        """Copy all files from source to destination directory.

        Args:
            src: Source directory
            dst: Destination directory
        """
        for item in os.listdir(src):
            s = os.path.join(src, item)
            d = os.path.join(dst, item)
            if os.path.isdir(s):
                os.makedirs(d, exist_ok=True)
                self._copy_directory(s, d)
            else:
                shutil.copy2(s, d)

    def _extract_wheel(self, wheel_path: str, extract_dir: str) -> None:
        """Extract a wheel package.

        Args:
            wheel_path: Path to the wheel file
            extract_dir: Directory to extract to
        """
        # Use zipfile to extract wheel (which is a zip file)
        import zipfile
        with zipfile.ZipFile(wheel_path, 'r') as zip_ref:
            zip_ref.extractall(extract_dir)

    def _extract_targz(self, targz_path: str, extract_dir: str) -> None:
        """Extract a tar.gz package.

        Args:
            targz_path: Path to the tar.gz file
            extract_dir: Directory to extract to
        """
        import tarfile
        with tarfile.open(targz_path, 'r:gz') as tar_ref:
            tar_ref.extractall(extract_dir)
            
    def _extract_zip(self, zip_path: str, extract_dir: str) -> None:
        """Extract a zip package.

        Args:
            zip_path: Path to the zip file
            extract_dir: Directory to extract to
        """
        import zipfile
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_dir)
            
    def _update_pyinstaller(self, app_dir: str, extract_dir: str, version_info: Dict) -> bool:
        """Update a PyInstaller package.

        Args:
            app_dir: Application directory path
            extract_dir: Directory with extracted update files
            version_info: Version information dictionary

        Returns:
            True if update succeeded, False otherwise
        """
        adapter = PackageAdapter.create_adapter('pyinstaller')
        return adapter.update(app_dir, extract_dir, version_info)
        
    def _update_nuitka(self, app_dir: str, extract_dir: str, version_info: Dict) -> bool:
        """Update a Nuitka package.

        Args:
            app_dir: Application directory path
            extract_dir: Directory with extracted update files
            version_info: Version information dictionary

        Returns:
            True if update succeeded, False otherwise
        """
        adapter = PackageAdapter.create_adapter('nuitka')
        return adapter.update(app_dir, extract_dir, version_info)
        
    def _update_hybrid(self, app_dir: str, extract_dir: str, version_info: Dict) -> bool:
        """Update a hybrid package (PyInstaller + Nuitka).

        Args:
            app_dir: Application directory path
            extract_dir: Directory with extracted update files
            version_info: Version information dictionary

        Returns:
            True if update succeeded, False otherwise
        """
        adapter = PackageAdapter.create_adapter('hybrid')
        return adapter.update(app_dir, extract_dir, version_info)
        
    def _update_standard(self, app_dir: str, extract_dir: str, version_info: Dict) -> bool:
        """Update a standard Python package.

        Args:
            app_dir: Application directory path
            extract_dir: Directory with extracted update files
            version_info: Version information dictionary

        Returns:
            True if update succeeded, False otherwise
        """
        adapter = PackageAdapter.create_adapter('standard')
        return adapter.update(app_dir, extract_dir, version_info)
        
    def _cleanup(self, download_path: str) -> None:
        """Clean up temporary files after update.

        Args:
            download_path: Path to the downloaded file
        """
        try:
            if os.path.exists(download_path):
                os.remove(download_path)
                logger.debug(f"Removed temporary file: {download_path}")
                
            # Clean up old backups, keeping only the last 3
            if os.path.exists(self.backup_dir):
                backups = [os.path.join(self.backup_dir, d) for d in os.listdir(self.backup_dir)
                          if os.path.isdir(os.path.join(self.backup_dir, d))]
                backups.sort(key=lambda x: os.path.getmtime(x), reverse=True)
                
                for old_backup in backups[3:]:
                    shutil.rmtree(old_backup, ignore_errors=True)
                    logger.debug(f"Removed old backup: {old_backup}")
                    
        except Exception as e:
            logger.warning(f"Cleanup failed: {str(e)}")
            # Non-critical error, just log it

    def _detect_build_type(self, app_dir: str) -> str:
        """Detect the build type of the application.

        Args:
            app_dir: Application directory path

        Returns:
            Build type: 'pyinstaller', 'nuitka', 'hybrid', or 'standard'
        """
        return PackageAdapter.detect_package_type(app_dir)