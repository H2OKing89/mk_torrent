"""
Integrations package for external APIs and services
"""

# Make audnexus API easily accessible
from .audnexus import AudnexusAPI, get_audnexus_metadata, get_audnexus_metadata_async

__all__ = ['AudnexusAPI', 'get_audnexus_metadata', 'get_audnexus_metadata_async']
