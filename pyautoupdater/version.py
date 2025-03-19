"""Version management module for PyAutoUpdater.

This module handles version checking, comparison, and retrieval from private PyPI repositories.
"""

import re
import logging
from typing import List, Dict, Optional, Tuple, Union, Callable
import requests
from packaging import version
from urllib.parse import urljoin
from requests.exceptions import RequestException

logger = logging.getLogger(__name__)


class VersionManager:
    """Manages version checking and comparison for the auto-updater."""

    def __init__(self, package_name: str, current_version: str, repositories: List[Dict[str, str]]):
        """Initialize the version manager.

        Args:
            package_name: Name of the package to check for updates
            current_version: Current version of the package
            repositories: List of repository configurations with the following keys:
                - url: Repository URL
                - username: Optional username for authentication
                - password: Optional password for authentication
                - verify_ssl: Whether to verify SSL certificates (default: True)
        """
        self.package_name = package_name
        self.current_version = version.parse(current_version)
        self.repositories = repositories
        self._latest_version = None
        self._latest_version_info = None

    def check_update(self, force_check: bool = False) -> Tuple[bool, Optional[str], Optional[Dict]]:
        """Check if an update is available.

        Args:
            force_check: Force a new check even if already checked

        Returns:
            Tuple containing:
                - Boolean indicating if an update is available
                - Latest version string if update is available, None otherwise
                - Version info dictionary if update is available, None otherwise
        """
        if self._latest_version is None or force_check:
            self._fetch_latest_version()

        if self._latest_version is None:
            return False, None, None

        update_available = self._latest_version > self.current_version
        if update_available:
            return True, str(self._latest_version), self._latest_version_info
        return False, None, None

    def _fetch_latest_version(self) -> None:
        """Fetch the latest version from configured repositories."""
        for repo in self.repositories:
            try:
                version_info = self._get_package_info_from_repo(repo)
                if version_info:
                    latest_version = version.parse(version_info.get('version', '0.0.0'))
                    
                    # Update if we don't have a version yet or if this one is newer
                    if (self._latest_version is None or 
                            latest_version > self._latest_version):
                        self._latest_version = latest_version
                        self._latest_version_info = version_info
            except Exception as e:
                logger.warning(f"Failed to fetch version from {repo['url']}: {str(e)}")
                continue

    def _get_package_info_from_repo(self, repo: Dict[str, str]) -> Optional[Dict]:
        """Get package information from a PyPI repository.

        Args:
            repo: Repository configuration dictionary

        Returns:
            Package information dictionary or None if not found
        """
        url = urljoin(repo['url'], f'pypi/{self.package_name}/json')
        auth = None
        if repo.get('username') and repo.get('password'):
            auth = (repo['username'], repo['password'])

        verify_ssl = repo.get('verify_ssl', True)

        try:
            response = requests.get(
                url, 
                auth=auth, 
                verify=verify_ssl,
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            
            # Extract the latest version info
            if 'info' in data:
                return {
                    'version': data['info'].get('version', '0.0.0'),
                    'download_url': self._extract_download_url(data),
                    'requires_python': data['info'].get('requires_python'),
                    'sha256': self._extract_sha256(data),
                    'metadata': data['info']
                }
            return None
        except RequestException as e:
            logger.error(f"Error fetching package info: {str(e)}")
            return None
        except ValueError as e:
            logger.error(f"Error parsing package info: {str(e)}")
            return None

    def _extract_download_url(self, data: Dict) -> Optional[str]:
        """Extract the download URL for the package wheel or sdist.

        Args:
            data: Package data from PyPI

        Returns:
            Download URL or None if not found
        """
        if 'urls' not in data or not data['urls']:
            return None

        # Prefer wheels over other formats
        for url_info in data['urls']:
            if url_info.get('packagetype') == 'bdist_wheel':
                return url_info.get('url')

        # Fall back to sdist if no wheel is available
        for url_info in data['urls']:
            if url_info.get('packagetype') == 'sdist':
                return url_info.get('url')

        # Return the first URL if no wheel or sdist is found
        return data['urls'][0].get('url') if data['urls'] else None

    def _extract_sha256(self, data: Dict) -> Optional[str]:
        """Extract the SHA256 hash for the package.

        Args:
            data: Package data from PyPI

        Returns:
            SHA256 hash or None if not found
        """
        if 'urls' not in data or not data['urls']:
            return None

        # Get SHA256 for the same file as the download URL
        download_url = self._extract_download_url(data)
        if not download_url:
            return None

        for url_info in data['urls']:
            if url_info.get('url') == download_url:
                return url_info.get('digests', {}).get('sha256')

        return None

    def is_update_required(self, min_required_version: str) -> bool:
        """Check if the current version is below a minimum required version.

        Args:
            min_required_version: Minimum version required

        Returns:
            True if update is required, False otherwise
        """
        min_version = version.parse(min_required_version)
        return self.current_version < min_version

    @staticmethod
    def compare_versions(version1: str, version2: str) -> int:
        """Compare two version strings.

        Args:
            version1: First version string
            version2: Second version string

        Returns:
            -1 if version1 < version2
             0 if version1 == version2
             1 if version1 > version2
        """
        v1 = version.parse(version1)
        v2 = version.parse(version2)

        if v1 < v2:
            return -1
        elif v1 > v2:
            return 1
        else:
            return 0