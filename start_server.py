#!/usr/bin/env python3

"""
Simple script to start the DeepResearch MCP server.
Run this with: python start_server.py
"""

import asyncio
from deepresearch.server import main

if __name__ == "__main__":
    print("Starting DeepResearch MCP server...")
    asyncio.run(main()) 