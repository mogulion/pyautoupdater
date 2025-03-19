"""Hooks management module for PyAutoUpdater.

This module provides a hook system for executing custom code before and after updates.
"""

import logging
from typing import Dict, List, Callable, Any, Optional

logger = logging.getLogger(__name__)


class HookManager:
    """Manages lifecycle hooks for the update process."""

    def __init__(self):
        """Initialize the hook manager."""
        self.pre_update_hooks = []
        self.post_update_hooks = []
        self.error_hooks = []

    def register_pre_update_hook(self, hook: Callable[[Dict], bool]) -> None:
        """Register a hook to be executed before an update.

        Args:
            hook: Function that takes version info dictionary and returns success boolean
        """
        self.pre_update_hooks.append(hook)
        logger.debug(f"Registered pre-update hook: {hook.__name__}")

    def register_post_update_hook(self, hook: Callable[[Dict], bool]) -> None:
        """Register a hook to be executed after an update.

        Args:
            hook: Function that takes version info dictionary and returns success boolean
        """
        self.post_update_hooks.append(hook)
        logger.debug(f"Registered post-update hook: {hook.__name__}")

    def register_error_hook(self, hook: Callable[[Exception, Dict], None]) -> None:
        """Register a hook to be executed when an error occurs during update.

        Args:
            hook: Function that takes exception and context dictionary
        """
        self.error_hooks.append(hook)
        logger.debug(f"Registered error hook: {hook.__name__}")

    def run_pre_update_hooks(self, version_info: Dict) -> bool:
        """Run all registered pre-update hooks.

        Args:
            version_info: Version information dictionary

        Returns:
            True if all hooks succeeded, False otherwise
        """
        logger.info("Running pre-update hooks")
        return self._run_hooks(self.pre_update_hooks, version_info)

    def run_post_update_hooks(self, version_info: Dict) -> bool:
        """Run all registered post-update hooks.

        Args:
            version_info: Version information dictionary

        Returns:
            True if all hooks succeeded, False otherwise
        """
        logger.info("Running post-update hooks")
        return self._run_hooks(self.post_update_hooks, version_info)

    def run_error_hooks(self, exception: Exception, context: Dict) -> None:
        """Run all registered error hooks.

        Args:
            exception: The exception that occurred
            context: Context information dictionary
        """
        logger.info("Running error hooks")
        for hook in self.error_hooks:
            try:
                hook(exception, context)
            except Exception as e:
                logger.error(f"Error in error hook {hook.__name__}: {str(e)}")

    def _run_hooks(self, hooks: List[Callable], version_info: Dict) -> bool:
        """Run a list of hooks with the given version info.

        Args:
            hooks: List of hook functions to run
            version_info: Version information dictionary

        Returns:
            True if all hooks succeeded, False otherwise
        """
        for hook in hooks:
            try:
                logger.debug(f"Running hook: {hook.__name__}")
                if not hook(version_info):
                    logger.error(f"Hook {hook.__name__} failed")
                    return False
            except Exception as e:
                logger.exception(f"Error in hook {hook.__name__}: {str(e)}")
                return False
        return True


# Common hook implementations
def config_migration_hook(version_info: Dict) -> bool:
    """Migrate configuration files to be compatible with the new version.

    Args:
        version_info: Version information dictionary

    Returns:
        True if migration succeeded, False otherwise
    """
    try:
        # Implementation would depend on specific application needs
        logger.info("Migrating configuration files")
        return True
    except Exception as e:
        logger.exception(f"Config migration failed: {str(e)}")
        return False


def service_restart_hook(version_info: Dict) -> bool:
    """Restart services after update.

    Args:
        version_info: Version information dictionary

    Returns:
        True if restart succeeded, False otherwise
    """
    try:
        # Implementation would depend on specific application needs
        logger.info("Restarting services")
        return True
    except Exception as e:
        logger.exception(f"Service restart failed: {str(e)}")
        return False


def environment_check_hook(version_info: Dict) -> bool:
    """Check if the environment is compatible with the new version.

    Args:
        version_info: Version information dictionary

    Returns:
        True if environment is compatible, False otherwise
    """
    try:
        # Implementation would depend on specific application needs
        logger.info("Checking environment compatibility")
        return True
    except Exception as e:
        logger.exception(f"Environment check failed: {str(e)}")
        return False