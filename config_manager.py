"""
Configuration management for DDL Wizard.
Supports YAML configuration files and environment profiles.
"""

import yaml
import os
import logging
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class DatabaseConnection:
    """Database connection configuration."""
    host: str
    port: int = 3306
    user: str = ""
    password: str = ""
    schema: str = ""
    
    def __post_init__(self):
        """Validate required fields."""
        if not all([self.host, self.user, self.schema]):
            raise ValueError("Host, user, and schema are required")


@dataclass
class SafetySettings:
    """Safety and validation settings."""
    enable_dry_run: bool = False
    require_confirmation: bool = True
    backup_before_migration: bool = True
    max_affected_rows: int = 10000
    dangerous_operations_allowed: bool = False
    validate_before_execution: bool = True


@dataclass
class OutputSettings:
    """Output and reporting settings."""
    output_dir: str = "./ddl_output"
    migration_file: str = "migration.sql"
    rollback_file: str = "rollback.sql"
    report_format: str = "text"  # text, json, markdown
    include_timestamps: bool = True
    color_output: bool = True


@dataclass
class DDLWizardConfig:
    """Complete DDL Wizard configuration."""
    source: DatabaseConnection
    destination: DatabaseConnection
    safety: SafetySettings = field(default_factory=SafetySettings)
    output: OutputSettings = field(default_factory=OutputSettings)
    environment: str = "development"
    log_level: str = "INFO"
    
    @classmethod
    def from_yaml(cls, config_path: str) -> 'DDLWizardConfig':
        """Load configuration from YAML file."""
        config_file = Path(config_path)
        if not config_file.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        
        with open(config_file, 'r') as f:
            data = yaml.safe_load(f)
        
        return cls.from_dict(data)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DDLWizardConfig':
        """Create configuration from dictionary."""
        # Parse source connection
        source_data = data.get('source', {})
        source = DatabaseConnection(**source_data)
        
        # Parse destination connection
        dest_data = data.get('destination', {})
        destination = DatabaseConnection(**dest_data)
        
        # Parse safety settings
        safety_data = data.get('safety', {})
        safety = SafetySettings(**safety_data)
        
        # Parse output settings
        output_data = data.get('output', {})
        output = OutputSettings(**output_data)
        
        return cls(
            source=source,
            destination=destination,
            safety=safety,
            output=output,
            environment=data.get('environment', 'development'),
            log_level=data.get('log_level', 'INFO')
        )
    
    def to_yaml(self, config_path: str):
        """Save configuration to YAML file."""
        config_dict = {
            'environment': self.environment,
            'log_level': self.log_level,
            'source': {
                'host': self.source.host,
                'port': self.source.port,
                'user': self.source.user,
                'password': self.source.password,
                'schema': self.source.schema
            },
            'destination': {
                'host': self.destination.host,
                'port': self.destination.port,
                'user': self.destination.user,
                'password': self.destination.password,
                'schema': self.destination.schema
            },
            'safety': {
                'enable_dry_run': self.safety.enable_dry_run,
                'require_confirmation': self.safety.require_confirmation,
                'backup_before_migration': self.safety.backup_before_migration,
                'max_affected_rows': self.safety.max_affected_rows,
                'dangerous_operations_allowed': self.safety.dangerous_operations_allowed,
                'validate_before_execution': self.safety.validate_before_execution
            },
            'output': {
                'output_dir': self.output.output_dir,
                'migration_file': self.output.migration_file,
                'rollback_file': self.output.rollback_file,
                'report_format': self.output.report_format,
                'include_timestamps': self.output.include_timestamps,
                'color_output': self.output.color_output
            }
        }
        
        with open(config_path, 'w') as f:
            yaml.dump(config_dict, f, default_flow_style=False, indent=2)
    
    def get_connection_string(self, connection_type: str) -> str:
        """Get connection string for source or destination."""
        conn = self.source if connection_type == 'source' else self.destination
        return f"{conn.user}@{conn.host}:{conn.port}/{conn.schema}"


class ConfigManager:
    """Manages configuration loading and environment profiles."""
    
    @staticmethod
    def create_sample_config(config_path: str):
        """Create a sample configuration file."""
        sample_config = DDLWizardConfig(
            source=DatabaseConnection(
                host="source.db.com",
                port=3306,
                user="readonly_user",
                password="${SOURCE_DB_PASSWORD}",
                schema="production_app"
            ),
            destination=DatabaseConnection(
                host="destination.db.com",
                port=3306,
                user="deploy_user", 
                password="${DEST_DB_PASSWORD}",
                schema="staging_app"
            ),
            safety=SafetySettings(
                enable_dry_run=True,
                require_confirmation=True,
                backup_before_migration=True,
                dangerous_operations_allowed=False
            ),
            output=OutputSettings(
                output_dir="./schema_migrations",
                migration_file="migration.sql",
                rollback_file="rollback.sql",
                report_format="text"
            ),
            environment="staging"
        )
        
        sample_config.to_yaml(config_path)
        logger.info(f"Sample configuration created: {config_path}")
    
    @staticmethod
    @staticmethod
    def load_config(config_path: Optional[str] = None, profile: Optional[str] = None) -> DDLWizardConfig:
        """Load configuration from file or environment variables."""
        # Try to find config file
        if config_path:
            config_file = Path(config_path)
        else:
            # Look for default config files
            possible_configs = [
                Path("ddl_wizard.yml"),
                Path("ddl_wizard.yaml"),
                Path("config/ddl_wizard.yml"),
                Path(".ddl_wizard.yml")
            ]
            
            config_file = None
            for possible_config in possible_configs:
                if possible_config.exists():
                    config_file = possible_config
                    break
        
        if config_file and config_file.exists():
            logger.info(f"Loading configuration from: {config_file}")
            
            # Load YAML and extract profile
            with open(config_file, 'r') as f:
                all_data = yaml.safe_load(f)
            
            # Use specified profile or default
            profile_name = profile or 'default'
            if profile_name in all_data:
                config_data = all_data[profile_name]
                logger.info(f"Using profile: {profile_name}")
            else:
                logger.warning(f"Profile '{profile_name}' not found, using default")
                config_data = all_data.get('default', all_data)
            
            config = DDLWizardConfig.from_dict(config_data)
            
            # Substitute environment variables
            config = ConfigManager._substitute_env_vars(config)
            return config
        
        # Fallback to environment variables or defaults
        logger.warning("No configuration file found, using environment variables/defaults")
        return ConfigManager._config_from_env()
    
    @staticmethod
    def _substitute_env_vars(config: DDLWizardConfig) -> DDLWizardConfig:
        """Substitute environment variables in configuration."""
        # Source connection
        if config.source.password.startswith('${') and config.source.password.endswith('}'):
            env_var = config.source.password[2:-1]
            config.source.password = os.getenv(env_var, '')
        
        # Destination connection
        if config.destination.password.startswith('${') and config.destination.password.endswith('}'):
            env_var = config.destination.password[2:-1]
            config.destination.password = os.getenv(env_var, '')
        
        return config
    
    @staticmethod
    def _config_from_env() -> DDLWizardConfig:
        """Create configuration from environment variables."""
        return DDLWizardConfig(
            source=DatabaseConnection(
                host=os.getenv('DDL_SOURCE_HOST', 'localhost'),
                port=int(os.getenv('DDL_SOURCE_PORT', '3306')),
                user=os.getenv('DDL_SOURCE_USER', ''),
                password=os.getenv('DDL_SOURCE_PASSWORD', ''),
                schema=os.getenv('DDL_SOURCE_SCHEMA', '')
            ),
            destination=DatabaseConnection(
                host=os.getenv('DDL_DEST_HOST', 'localhost'),
                port=int(os.getenv('DDL_DEST_PORT', '3306')),
                user=os.getenv('DDL_DEST_USER', ''),
                password=os.getenv('DDL_DEST_PASSWORD', ''),
                schema=os.getenv('DDL_DEST_SCHEMA', '')
            ),
            environment=os.getenv('DDL_ENVIRONMENT', 'development'),
            log_level=os.getenv('DDL_LOG_LEVEL', 'INFO')
        )
