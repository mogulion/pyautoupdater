"""PyAutoUpdater - A comprehensive auto-update solution for Python applications.

This library provides standardized auto-update functionality for Python-based compiled tools,
supporting version detection, incremental updates, and pre/post-update processing.
"""

__version__ = "0.1.0"

# Import core classes for easy access
from .updater import UpdateManager
from .hooks import HookManager
from .security import SecurityManager
from .delta import DeltaManager
from .version import VersionManager
from .packagers import PackageAdapter, PyInstallerAdapter, NuitkaAdapter, HybridAdapter, StandardAdapter

# Define what's available when using "from pyautoupdater import *"
__all__ = [
    'UpdateManager',
    'HookManager',
    'SecurityManager',
    'DeltaManager',
    'VersionManager',
    'PackageAdapter',
    'PyInstallerAdapter',
    'NuitkaAdapter',
    'HybridAdapter',
    'StandardAdapter'
]