"""
Copyright (C) 2025 Claudio Nanni
This file is part of DDL Wizard.

DDL Wizard is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

DDL Wizard is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with DDL Wizard.  If not, see <https://www.gnu.org/licenses/>.
"""

"""
Interactive mode manager for DDL Wizard.
"""

import logging

logger = logging.getLogger(__name__)


class InteractiveModeManager:
    """Manages interactive user prompts and confirmations."""
    
    def __init__(self):
        """Initialize interactive mode manager."""
        pass
    
    def confirm_migration(self, source_schema: str, dest_schema: str, 
                         operation_count: int, safety_warnings: list) -> bool:
        """
        Prompt user to confirm migration execution.
        
        Args:
            source_schema: Source schema name
            dest_schema: Destination schema name
            operation_count: Number of operations to execute
            safety_warnings: List of safety warnings
            
        Returns:
            bool: True if user confirms, False otherwise
        """
        print(f"\n📋 Migration Summary:")
        print(f"   Source: {source_schema}")
        print(f"   Destination: {dest_schema}")
        print(f"   Operations: {operation_count}")
        print(f"   Warnings: {len(safety_warnings)}")
        
        if safety_warnings:
            print(f"\n⚠️ Safety Warnings:")
            for warning in safety_warnings:
                print(f"   - {warning.level.value}: {warning.message}")
        
        response = input(f"\n❓ Do you want to proceed with this migration? (y/N): ").strip().lower()
        return response in ['y', 'yes']
    
    def prompt_for_confirmation(self, message: str) -> bool:
        """
        Simple confirmation prompt.
        
        Args:
            message: Message to display
            
        Returns:
            bool: True if user confirms, False otherwise
        """
        response = input(f"{message} (y/N): ").strip().lower()
        return response in ['y', 'yes']
