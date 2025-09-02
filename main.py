#!/usr/bin/env python3
"""
DDL Wizard CLI Entry Point
==========================

This script provides backward compatibility for users who want to run ddlwizard
directly from the root directory.
"""

if __name__ == "__main__":
    from ddlwizard.cli import main
    main()
