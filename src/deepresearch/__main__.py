#!/usr/bin/env python3

"""
Main entry point for the deepresearch package when executed as `python -m deepresearch`.
"""

import asyncio
from .server import main

if __name__ == "__main__":
    asyncio.run(main()) 