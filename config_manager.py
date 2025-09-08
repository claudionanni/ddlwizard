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
Configuration management for DDL Wizard.
"""

from dataclasses import dataclass
from typing import Optional
import yaml


@dataclass
class DatabaseConnection:
    """Database connection configuration."""
    host: str
    port: int
    user: str
    password: str
    schema: str


@dataclass
class SafetySettings:
    """Safety analysis settings."""
    validate_before_execution: bool = True
    allow_data_loss_operations: bool = False
    require_confirmation: bool = True
    max_operations_without_confirmation: int = 10


@dataclass
class OutputSettings:
    """Output file settings."""
    output_dir: str = "./ddl_output"
    migration_file: str = "migration.sql"
    rollback_file: str = "rollback.sql"
    generate_documentation: bool = True
    documentation_format: str = "html"


@dataclass
class DatabaseSettings:
    """Database-specific settings."""
    connection_timeout: int = 30
    query_timeout: int = 60
    max_connections: int = 5
    use_ssl: bool = False


@dataclass  
class DDLWizardConfig:
    """Main configuration for DDL Wizard."""
    source: DatabaseConnection
    destination: DatabaseConnection
    safety: SafetySettings
    output: OutputSettings
    database: Optional[DatabaseSettings] = None
    
    @classmethod
    def load_config(cls, config_file: str, profile: Optional[str] = None) -> 'DDLWizardConfig':
        """Load configuration from YAML file."""
        with open(config_file, 'r') as f:
            config_data = yaml.safe_load(f)
        
        if profile and profile in config_data:
            config_data = config_data[profile]
        
        # Extract database connections
        source_data = config_data.get('source', {})
        dest_data = config_data.get('destination', {})
        
        source = DatabaseConnection(
            host=source_data.get('host', 'localhost'),
            port=source_data.get('port', 3306),
            user=source_data.get('user', 'root'),
            password=source_data.get('password', ''),
            schema=source_data.get('schema', '')
        )
        
        destination = DatabaseConnection(
            host=dest_data.get('host', 'localhost'),
            port=dest_data.get('port', 3306),
            user=dest_data.get('user', 'root'),
            password=dest_data.get('password', ''),
            schema=dest_data.get('schema', '')
        )
        
        # Extract settings
        safety_data = config_data.get('safety', {})
        safety = SafetySettings(
            validate_before_execution=safety_data.get('validate_before_execution', True),
            allow_data_loss_operations=safety_data.get('allow_data_loss_operations', False),
            require_confirmation=safety_data.get('require_confirmation', True),
            max_operations_without_confirmation=safety_data.get('max_operations_without_confirmation', 10)
        )
        
        output_data = config_data.get('output', {})
        output = OutputSettings(
            output_dir=output_data.get('output_dir', './ddl_output'),
            migration_file=output_data.get('migration_file', 'migration.sql'),
            rollback_file=output_data.get('rollback_file', 'rollback.sql'),
            generate_documentation=output_data.get('generate_documentation', True),
            documentation_format=output_data.get('documentation_format', 'html')
        )
        
        database_data = config_data.get('database', {})
        database = DatabaseSettings(
            connection_timeout=database_data.get('connection_timeout', 30),
            query_timeout=database_data.get('query_timeout', 60),
            max_connections=database_data.get('max_connections', 5),
            use_ssl=database_data.get('use_ssl', False)
        ) if database_data else None
        
        return cls(
            source=source,
            destination=destination,
            safety=safety,
            output=output,
            database=database
        )
