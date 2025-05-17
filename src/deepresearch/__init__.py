from . import server
from .orchestration import DeepResearchOrchestrator
import asyncio

def main():
    """Main entry point for the package."""
    asyncio.run(server.main())

# Expose the core components
__all__ = ['main', 'server', 'DeepResearchOrchestrator']