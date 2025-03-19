"""Package adapters module for PyAutoUpdater.

This module provides adapters for different packaging tools (PyInstaller, Nuitka, etc.)
to handle their specific update requirements.
"""

import os
import sys
import logging
import platform
import shutil
from typing import Dict, Optional, List, Tuple, Any
from pathlib import Path

logger = logging.getLogger(__name__)


class PackageAdapter:
    """Base class for package adapters."""

    @staticmethod
    def detect_package_type(app_dir: str) -> str:
        """Detect the package type based on directory structure and files.

        Args:
            app_dir: Application directory path

        Returns:
            Package type: 'pyinstaller', 'nuitka', 'hybrid', or 'standard'
        """
        is_pyinstaller = PackageAdapter._is_pyinstaller(app_dir)
        is_nuitka = PackageAdapter._is_nuitka(app_dir)

        if is_pyinstaller and is_nuitka:
            return 'hybrid'
        elif is_pyinstaller:
            return 'pyinstaller'
        elif is_nuitka:
            return 'nuitka'
        else:
            return 'standard'

    @staticmethod
    def _is_pyinstaller(app_dir: str) -> bool:
        """Check if the application is packaged with PyInstaller.

        Args:
            app_dir: Application directory path

        Returns:
            True if PyInstaller package, False otherwise
        """
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        if hasattr(sys, '_MEIPASS'):
            return True

        # Check for PyInstaller-specific files and directories
        pyinstaller_markers = [
            '_MEI', 'pyiboot', 'pyimod', 'pyi-runtime-tmpdir',
            'base_library.zip', 'PYZ-', '.pkg'
        ]

        for marker in pyinstaller_markers:
            for item in os.listdir(app_dir):
                if marker in item:
                    return True

        return False

    @staticmethod
    def _is_nuitka(app_dir: str) -> bool:
        """Check if the application is packaged with Nuitka.

        Args:
            app_dir: Application directory path

        Returns:
            True if Nuitka package, False otherwise
        """
        # Check for Nuitka-specific files and directories
        nuitka_markers = [
            '.pyi', '.pyd', '.so.pyi', '.bin', '.const', 
            'module.', '.nuitka', 'nuitka-runtime'
        ]

        for marker in nuitka_markers:
            for item in os.listdir(app_dir):
                if marker in item:
                    return True

        return False

    @staticmethod
    def create_adapter(package_type: str) -> 'PackageAdapter':
        """Create the appropriate adapter for the package type.

        Args:
            package_type: Type of package ('pyinstaller', 'nuitka', 'hybrid', or 'standard')

        Returns:
            Package adapter instance
        """
        if package_type == 'pyinstaller':
            return PyInstallerAdapter()
        elif package_type == 'nuitka':
            return NuitkaAdapter()
        elif package_type == 'hybrid':
            return HybridAdapter()
        else:
            return StandardAdapter()

    def update(self, app_dir: str, extract_dir: str, version_info: Dict) -> bool:
        """Update the application.

        Args:
            app_dir: Application directory path
            extract_dir: Directory with extracted update files
            version_info: Version information dictionary

        Returns:
            True if update succeeded, False otherwise
        """
        raise NotImplementedError("Subclasses must implement this method")

    def _get_update_files(self, extract_dir: str) -> List[str]:
        """Get the list of files to update.

        Args:
            extract_dir: Directory with extracted update files

        Returns:
            List of file paths to update
        """
        update_files = []
        for root, _, files in os.walk(extract_dir):
            for file in files:
                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, extract_dir)
                update_files.append(rel_path)
        return update_files

    def _copy_update_files(self, app_dir: str, extract_dir: str, update_files: List[str]) -> bool:
        """Copy update files to the application directory.

        Args:
            app_dir: Application directory path
            extract_dir: Directory with extracted update files
            update_files: List of file paths to update

        Returns:
            True if copy succeeded, False otherwise
        """
        try:
            for file in update_files:
                src_path = os.path.join(extract_dir, file)
                dst_path = os.path.join(app_dir, file)

                # Create directory if it doesn't exist
                os.makedirs(os.path.dirname(dst_path), exist_ok=True)

                # Copy the file
                shutil.copy2(src_path, dst_path)
                logger.debug(f"Copied {src_path} to {dst_path}")

            return True
        except Exception as e:
            logger.exception(f"Failed to copy update files: {str(e)}")
            return False


class PyInstallerAdapter(PackageAdapter):
    """Adapter for PyInstaller packages."""

    def update(self, app_dir: str, extract_dir: str, version_info: Dict) -> bool:
        """Update a PyInstaller package.

        Args:
            app_dir: Application directory path
            extract_dir: Directory with extracted update files
            version_info: Version information dictionary

        Returns:
            True if update succeeded, False otherwise
        """
        logger.info("Updating PyInstaller package")

        try:
            # Get the list of files to update
            update_files = self._get_update_files(extract_dir)

            # Filter out PyInstaller-specific files that should not be updated
            filtered_files = self._filter_pyinstaller_files(update_files)

            # Copy the update files
            if not self._copy_update_files(app_dir, extract_dir, filtered_files):
                return False

            # Handle PyInstaller-specific post-update tasks
            self._handle_pyinstaller_specific_tasks(app_dir, version_info)

            return True
        except Exception as e:
            logger.exception(f"PyInstaller update failed: {str(e)}")
            return False

    def _filter_pyinstaller_files(self, files: List[str]) -> List[str]:
        """Filter out PyInstaller-specific files that should not be updated.

        Args:
            files: List of file paths

        Returns:
            Filtered list of file paths
        """
        # Files that should not be updated in a PyInstaller package
        excluded_patterns = [
            'base_library.zip', '_MEI', 'pyiboot', 'pyimod',
            'pyi-runtime-tmpdir', '.pkg', 'PYZ-'
        ]

        filtered = []
        for file in files:
            exclude = False
            for pattern in excluded_patterns:
                if pattern in file:
                    exclude = True
                    break
            if not exclude:
                filtered.append(file)

        return filtered

    def _handle_pyinstaller_specific_tasks(self, app_dir: str, version_info: Dict) -> None:
        """Handle PyInstaller-specific post-update tasks.

        Args:
            app_dir: Application directory path
            version_info: Version information dictionary
        """
        # Implementation depends on specific application needs
        # For example, updating .pkg files or other PyInstaller-specific resources
        pass


class NuitkaAdapter(PackageAdapter):
    """Adapter for Nuitka packages."""

    def update(self, app_dir: str, extract_dir: str, version_info: Dict) -> bool:
        """Update a Nuitka package.

        Args:
            app_dir: Application directory path
            extract_dir: Directory with extracted update files
            version_info: Version information dictionary

        Returns:
            True if update succeeded, False otherwise
        """
        logger.info("Updating Nuitka package")

        try:
            # Get the list of files to update
            update_files = self._get_update_files(extract_dir)

            # Filter out Nuitka-specific files that should not be updated
            filtered_files = self._filter_nuitka_files(update_files)

            # Copy the update files
            if not self._copy_update_files(app_dir, extract_dir, filtered_files):
                return False

            # Handle Nuitka-specific post-update tasks
            self._handle_nuitka_specific_tasks(app_dir, version_info)

            return True
        except Exception as e:
            logger.exception(f"Nuitka update failed: {str(e)}")
            return False

    def _filter_nuitka_files(self, files: List[str]) -> List[str]:
        """Filter out Nuitka-specific files that should not be updated.

        Args:
            files: List of file paths

        Returns:
            Filtered list of file paths
        """
        # Files that should not be updated in a Nuitka package
        excluded_patterns = [
            '.pyi', '.const', 'module.', '.nuitka', 'nuitka-runtime'
        ]

        filtered = []
        for file in files:
            exclude = False
            for pattern in excluded_patterns:
                if pattern in file:
                    exclude = True
                    break
            if not exclude:
                filtered.append(file)

        return filtered

    def _handle_nuitka_specific_tasks(self, app_dir: str, version_info: Dict) -> None:
        """Handle Nuitka-specific post-update tasks.

        Args:
            app_dir: Application directory path
            version_info: Version information dictionary
        """
        # Implementation depends on specific application needs
        # For example, updating .pyi files or other Nuitka-specific resources
        pass


class HybridAdapter(PackageAdapter):
    """Adapter for hybrid packages (PyInstaller + Nuitka)."""

    def update(self, app_dir: str, extract_dir: str, version_info: Dict) -> bool:
        """Update a hybrid package.

        Args:
            app_dir: Application directory path
            extract_dir: Directory with extracted update files
            version_info: Version information dictionary

        Returns:
            True if update succeeded, False otherwise
        """
        logger.info("Updating hybrid package (PyInstaller + Nuitka)")

        try:
            # Get the list of files to update
            update_files = self._get_update_files(extract_dir)

            # Filter out both PyInstaller and Nuitka specific files
            filtered_files = self._filter_hybrid_files(update_files)

            # Copy the update files
            if not self._copy_update_files(app_dir, extract_dir, filtered_files):
                return False

            # Handle hybrid-specific post-update tasks
            self._handle_hybrid_specific_tasks(app_dir, version_info)

            return True
        except Exception as e:
            logger.exception(f"Hybrid update failed: {str(e)}")
            return False

    def _filter_hybrid_files(self, files: List[str]) -> List[str]:
        """Filter out both PyInstaller and Nuitka specific files.

        Args:
            files: List of file paths

        Returns:
            Filtered list of file paths
        """
        # Combine excluded patterns from both PyInstaller and Nuitka
        excluded_patterns = [
            # PyInstaller patterns
            'base_library.zip', '_MEI', 'pyiboot', 'pyimod',
            'pyi-runtime-tmpdir', '.pkg', 'PYZ-',
            # Nuitka patterns
            '.pyi', '.const', 'module.', '.nuitka', 'nuitka-runtime'
        ]

        filtered = []
        for file in files:
            exclude = False
            for pattern in excluded_patterns:
                if pattern in file:
                    exclude = True
                    break
            if not exclude:
                filtered.append(file)

        return filtered

    def _handle_hybrid_specific_tasks(self, app_dir: str, version_info: Dict) -> None:
        """Handle hybrid-specific post-update tasks.

        Args:
            app_dir: Application directory path
            version_info: Version information dictionary
        """
        # Implementation depends on specific application needs
        # For example, updating both PyInstaller and Nuitka specific resources
        pass


class StandardAdapter(PackageAdapter):
    """Adapter for standard Python packages."""

    def update(self, app_dir: str, extract_dir: str, version_info: Dict) -> bool:
        """Update a standard Python package.

        Args:
            app_dir: Application directory path
            extract_dir: Directory with extracted update files
            version_info: Version information dictionary

        Returns:
            True if update succeeded, False otherwise
        """
        logger.info("Updating standard Python package")

        try:
            # Get the list of files to update
            update_files = self._get_update_files(extract_dir)

            # Copy the update files
            if not self._copy_update_files(app_dir, extract_dir, update_files):
                return False

            return True
        except Exception as e:
            logger.exception(f"Standard package update failed: {str(e)}")
            return False