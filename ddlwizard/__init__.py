"""
DDL Wizard - Database DDL Extraction and Comparison Tool
========================================================

A comprehensive tool for extracting DDL objects from databases, managing them in git,
and generating migration scripts for schema synchronization.
"""

__version__ = "1.0.0"
__author__ = "Claudio Nanni"

# Import main classes for easy access
from .core import DDLWizardCore
from .cli import main as cli_main
from .gui import main as gui_main

__all__ = ['DDLWizardCore', 'cli_main', 'gui_main']
