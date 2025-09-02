"""Workflow modules for automated processes."""

def __getattr__(name):
    """Lazy import to avoid circular dependencies."""
    if name == "upload_workflow":
        from .upload_integration import upload_workflow
        return upload_workflow
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
