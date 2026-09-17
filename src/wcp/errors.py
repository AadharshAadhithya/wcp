"""Domain errors surfaced by the WCP command line interface."""


class WcpError(Exception):
    """Base class for expected, user-actionable WCP errors."""


class GitError(WcpError):
    """Raised when a repository cannot be inspected."""


class ManifestError(WcpError):
    """Raised when a project manifest cannot be read or validated."""


class InitializationConflict(WcpError):
    """Raised when init arguments disagree with an existing project identity."""
