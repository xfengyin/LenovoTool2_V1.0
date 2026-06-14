"""Custom exception hierarchy for the Lenovo Battery Tool."""


class LenovoToolError(Exception):
    """Base exception for all application errors."""


class DLLNotFoundError(LenovoToolError):
    """A required DLL file was not found."""


class DLLCommunicationError(LenovoToolError):
    """The DLL call failed or returned an error code."""


class SMBusError(DLLCommunicationError):
    """SMBus communication error with specific code."""


class ConfigurationError(LenovoToolError):
    """Invalid configuration value."""


class ChargeModeError(LenovoToolError):
    """Failed to switch charge mode."""
