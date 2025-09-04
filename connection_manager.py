"""
Connection Manager for DDL Wizard
=================================

Manages saved database connection configurations.
Provides functionality to save, load, delete, and list connection profiles.
"""

import json
import os
from pathlib import Path
from typing import Dict, List, Optional
from database import DatabaseConfig
import logging

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages saved database connections."""
    
    def __init__(self, config_dir: str = None):
        """
        Initialize connection manager.
        
        Args:
            config_dir: Directory to store connection configs (default: ~/.ddlwizard)
        """
        if config_dir is None:
            config_dir = os.path.expanduser("~/.ddlwizard")
        
        self.config_dir = Path(config_dir)
        self.connections_file = self.config_dir / "connections.json"
        
        # Create config directory if it doesn't exist
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize connections file if it doesn't exist
        if not self.connections_file.exists():
            self._save_connections({})
    
    def save_connection(self, name: str, config: DatabaseConfig, description: str = "") -> bool:
        """
        Save a database connection configuration.
        
        Args:
            name: Unique name for the connection
            config: Database configuration to save
            description: Optional description for the connection
            
        Returns:
            bool: True if saved successfully, False otherwise
        """
        try:
            connections = self._load_connections()
            
            # Convert DatabaseConfig to dictionary (without password for security)
            connection_data = {
                "host": config.host,
                "port": config.port,
                "user": config.user,
                "schema": config.schema,
                "description": description,
                "created_at": self._get_timestamp(),
                "last_used": None
            }
            
            connections[name] = connection_data
            self._save_connections(connections)
            
            logger.info(f"Saved connection profile: {name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save connection {name}: {e}")
            return False
    
    def load_connection(self, name: str) -> Optional[DatabaseConfig]:
        """
        Load a database connection configuration.
        
        Args:
            name: Name of the connection to load
            
        Returns:
            DatabaseConfig: Loaded configuration (without password) or None if not found
        """
        try:
            connections = self._load_connections()
            
            if name not in connections:
                logger.warning(f"Connection profile not found: {name}")
                return None
            
            conn_data = connections[name]
            
            # Update last used timestamp
            conn_data["last_used"] = self._get_timestamp()
            connections[name] = conn_data
            self._save_connections(connections)
            
            # Return DatabaseConfig (user will need to enter password)
            config = DatabaseConfig(
                host=conn_data["host"],
                port=conn_data["port"],
                user=conn_data["user"],
                password="",  # Password not stored for security
                schema=conn_data["schema"]
            )
            
            logger.info(f"Loaded connection profile: {name}")
            return config
            
        except Exception as e:
            logger.error(f"Failed to load connection {name}: {e}")
            return None
    
    def list_connections(self) -> Dict[str, Dict]:
        """
        List all saved connection configurations.
        
        Returns:
            Dict: Dictionary of connection names and their metadata
        """
        try:
            connections = self._load_connections()
            
            # Return connection metadata (without sensitive information)
            result = {}
            for name, data in connections.items():
                result[name] = {
                    "host": data["host"],
                    "port": data["port"],
                    "user": data["user"],
                    "schema": data["schema"],
                    "description": data.get("description", ""),
                    "created_at": data.get("created_at", "Unknown"),
                    "last_used": data.get("last_used", "Never")
                }
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to list connections: {e}")
            return {}
    
    def delete_connection(self, name: str) -> bool:
        """
        Delete a saved connection configuration.
        
        Args:
            name: Name of the connection to delete
            
        Returns:
            bool: True if deleted successfully, False otherwise
        """
        try:
            connections = self._load_connections()
            
            if name not in connections:
                logger.warning(f"Connection profile not found: {name}")
                return False
            
            del connections[name]
            self._save_connections(connections)
            
            logger.info(f"Deleted connection profile: {name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete connection {name}: {e}")
            return False
    
    def update_connection(self, name: str, config: DatabaseConfig, description: str = None) -> bool:
        """
        Update an existing connection configuration.
        
        Args:
            name: Name of the connection to update
            config: New database configuration
            description: New description (if provided)
            
        Returns:
            bool: True if updated successfully, False otherwise
        """
        try:
            connections = self._load_connections()
            
            if name not in connections:
                logger.warning(f"Connection profile not found: {name}")
                return False
            
            # Update connection data
            existing_data = connections[name]
            existing_data.update({
                "host": config.host,
                "port": config.port,
                "user": config.user,
                "schema": config.schema,
                "last_used": self._get_timestamp()
            })
            
            if description is not None:
                existing_data["description"] = description
            
            connections[name] = existing_data
            self._save_connections(connections)
            
            logger.info(f"Updated connection profile: {name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update connection {name}: {e}")
            return False
    
    def connection_exists(self, name: str) -> bool:
        """
        Check if a connection with the given name exists.
        
        Args:
            name: Name to check
            
        Returns:
            bool: True if connection exists, False otherwise
        """
        connections = self._load_connections()
        return name in connections
    
    def get_connection_info(self, name: str) -> Optional[Dict]:
        """
        Get information about a specific connection.
        
        Args:
            name: Name of the connection
            
        Returns:
            Dict: Connection information or None if not found
        """
        connections = self._load_connections()
        return connections.get(name)
    
    def export_connections(self, export_path: str, include_passwords: bool = False) -> bool:
        """
        Export all connections to a file.
        
        Args:
            export_path: Path to export the connections to
            include_passwords: Whether to include passwords (not recommended)
            
        Returns:
            bool: True if exported successfully, False otherwise
        """
        try:
            connections = self._load_connections()
            
            # Create export data
            export_data = {
                "ddlwizard_connections": connections,
                "exported_at": self._get_timestamp(),
                "version": "1.0"
            }
            
            with open(export_path, 'w') as f:
                json.dump(export_data, f, indent=2)
            
            logger.info(f"Exported {len(connections)} connections to {export_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to export connections: {e}")
            return False
    
    def import_connections(self, import_path: str, overwrite: bool = False) -> int:
        """
        Import connections from a file.
        
        Args:
            import_path: Path to import the connections from
            overwrite: Whether to overwrite existing connections
            
        Returns:
            int: Number of connections imported
        """
        try:
            with open(import_path, 'r') as f:
                import_data = json.load(f)
            
            if "ddlwizard_connections" not in import_data:
                logger.error("Invalid import file format")
                return 0
            
            imported_connections = import_data["ddlwizard_connections"]
            existing_connections = self._load_connections()
            
            imported_count = 0
            for name, data in imported_connections.items():
                if name in existing_connections and not overwrite:
                    logger.warning(f"Skipping existing connection: {name}")
                    continue
                
                existing_connections[name] = data
                imported_count += 1
            
            self._save_connections(existing_connections)
            logger.info(f"Imported {imported_count} connections from {import_path}")
            return imported_count
            
        except Exception as e:
            logger.error(f"Failed to import connections: {e}")
            return 0
    
    def _load_connections(self) -> Dict:
        """Load connections from the JSON file."""
        try:
            with open(self.connections_file, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}
    
    def _save_connections(self, connections: Dict) -> None:
        """Save connections to the JSON file."""
        with open(self.connections_file, 'w') as f:
            json.dump(connections, f, indent=2)
    
    def _get_timestamp(self) -> str:
        """Get current timestamp as string."""
        from datetime import datetime
        return datetime.now().isoformat()


# Convenience functions for global usage
_global_manager = None


def get_connection_manager() -> ConnectionManager:
    """Get the global connection manager instance."""
    global _global_manager
    if _global_manager is None:
        _global_manager = ConnectionManager()
    return _global_manager


def save_connection(name: str, config: DatabaseConfig, description: str = "") -> bool:
    """Save a connection using the global manager."""
    return get_connection_manager().save_connection(name, config, description)


def load_connection(name: str) -> Optional[DatabaseConfig]:
    """Load a connection using the global manager."""
    return get_connection_manager().load_connection(name)


def list_connections() -> Dict[str, Dict]:
    """List all connections using the global manager."""
    return get_connection_manager().list_connections()


def delete_connection(name: str) -> bool:
    """Delete a connection using the global manager."""
    return get_connection_manager().delete_connection(name)
