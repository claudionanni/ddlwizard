"""
Safety analyzer for DDL Wizard.
Detects potentially dangerous operations and data loss scenarios.
"""

import logging
from typing import List, Dict, Any, Set, Tuple
from enum import Enum
from dataclasses import dataclass
from ddl_analyzer import ChangeType, ColumnDefinition, TableStructure

logger = logging.getLogger(__name__)


class RiskLevel(Enum):
    """Risk levels for database operations."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


@dataclass
class SafetyWarning:
    """Represents a safety warning for a database operation."""
    risk_level: RiskLevel
    operation: str
    table_name: str
    description: str
    recommendation: str
    affected_data: str = ""
    
    def __str__(self):
        risk_emoji = {
            RiskLevel.LOW: "🟢",
            RiskLevel.MEDIUM: "🟡", 
            RiskLevel.HIGH: "🟠",
            RiskLevel.CRITICAL: "🔴"
        }
        
        return f"{risk_emoji[self.risk_level]} {self.risk_level.value}: {self.description}"


class SafetyAnalyzer:
    """Analyzes database operations for potential data loss and safety issues."""
    
    def __init__(self):
        # Data types that are incompatible for conversion
        self.incompatible_types = {
            ('varchar', 'int'): True,
            ('text', 'int'): True,
            ('json', 'varchar'): True,
            ('datetime', 'varchar'): True,
            ('decimal', 'varchar'): True
        }
        
        # Operations that can cause data loss
        self.risky_operations = {
            ChangeType.DROP_COLUMN: RiskLevel.HIGH,
            ChangeType.DROP_INDEX: RiskLevel.MEDIUM,
            ChangeType.CHANGE_ENGINE: RiskLevel.MEDIUM,
        }
    
    def analyze_migration_safety(self, table_name: str, differences: List[Dict[str, Any]], 
                                source_structure: TableStructure, dest_structure: TableStructure) -> List[SafetyWarning]:
        """Analyze a table migration for safety issues."""
        warnings = []
        
        for diff in differences:
            change_type = diff['type']
            
            if change_type == ChangeType.DROP_COLUMN:
                warning = self._analyze_column_drop(table_name, diff['column'])
                warnings.append(warning)
            
            elif change_type == ChangeType.MODIFY_COLUMN:
                warning = self._analyze_column_modification(
                    table_name, diff['column_name'], diff['from'], diff['to']
                )
                if warning:
                    warnings.append(warning)
            
            elif change_type == ChangeType.ADD_COLUMN:
                warning = self._analyze_column_addition(table_name, diff['column'])
                if warning:
                    warnings.append(warning)
            
            elif change_type == ChangeType.DROP_INDEX:
                warning = self._analyze_index_drop(table_name, diff['index'])
                warnings.append(warning)
            
            elif change_type == ChangeType.CHANGE_ENGINE:
                warning = self._analyze_engine_change(table_name, diff['from'], diff['to'])
                warnings.append(warning)
            
            elif change_type == ChangeType.CHANGE_CHARSET:
                warning = self._analyze_charset_change(table_name, diff['from'], diff['to'])
                if warning:
                    warnings.append(warning)
        
        return warnings
    
    def _analyze_column_drop(self, table_name: str, column: ColumnDefinition) -> SafetyWarning:
        """Analyze column drop operation."""
        return SafetyWarning(
            risk_level=RiskLevel.CRITICAL,
            operation="DROP COLUMN",
            table_name=table_name,
            description=f"Dropping column '{column.name}' will permanently delete all data in this column",
            recommendation="Backup the column data before proceeding. Consider renaming instead of dropping.",
            affected_data=f"All data in column '{column.name}'"
        )
    
    def _analyze_column_modification(self, table_name: str, column_name: str, 
                                   from_col: ColumnDefinition, to_col: ColumnDefinition) -> SafetyWarning:
        """Analyze column modification operation."""
        warnings = []
        risk_level = RiskLevel.LOW
        issues = []
        
        # Check data type compatibility
        from_type = self._extract_base_type(from_col.data_type)
        to_type = self._extract_base_type(to_col.data_type)
        
        if self._are_types_incompatible(from_type, to_type):
            risk_level = RiskLevel.CRITICAL
            issues.append(f"Incompatible type conversion: {from_type} → {to_type}")
        
        # Check size reduction
        if self._is_size_reduction(from_col.data_type, to_col.data_type):
            risk_level = max(risk_level, RiskLevel.HIGH)
            issues.append(f"Data truncation risk: {from_col.data_type} → {to_col.data_type}")
        
        # Check nullability change
        if from_col.nullable and not to_col.nullable:
            risk_level = max(risk_level, RiskLevel.HIGH)
            issues.append("Adding NOT NULL constraint to nullable column")
        
        # Check default value changes
        if from_col.default != to_col.default:
            risk_level = max(risk_level, RiskLevel.MEDIUM)
            issues.append(f"Default value change: '{from_col.default}' → '{to_col.default}'")
        
        if issues:
            return SafetyWarning(
                risk_level=risk_level,
                operation="MODIFY COLUMN",
                table_name=table_name,
                description=f"Column '{column_name}' modification has risks: {'; '.join(issues)}",
                recommendation=self._get_modify_recommendation(risk_level),
                affected_data=f"All data in column '{column_name}'"
            )
        
        return None
    
    def _analyze_column_addition(self, table_name: str, column: ColumnDefinition) -> SafetyWarning:
        """Analyze column addition operation."""
        if not column.nullable and column.default is None:
            return SafetyWarning(
                risk_level=RiskLevel.MEDIUM,
                operation="ADD COLUMN",
                table_name=table_name,
                description=f"Adding NOT NULL column '{column.name}' without default value",
                recommendation="Consider adding a default value or making the column nullable",
                affected_data="May fail if table contains existing data"
            )
        return None
    
    def _analyze_index_drop(self, table_name: str, index) -> SafetyWarning:
        """Analyze index drop operation."""
        if index.is_primary:
            risk_level = RiskLevel.CRITICAL
            description = f"Dropping PRIMARY KEY will remove table's primary key constraint"
            recommendation = "Ensure you have a replacement primary key strategy"
        elif index.is_unique:
            risk_level = RiskLevel.HIGH
            description = f"Dropping UNIQUE index '{index.name}' will remove uniqueness constraint"
            recommendation = "Verify that duplicate values are acceptable"
        else:
            risk_level = RiskLevel.MEDIUM
            description = f"Dropping index '{index.name}' may impact query performance"
            recommendation = "Monitor query performance after this change"
        
        return SafetyWarning(
            risk_level=risk_level,
            operation="DROP INDEX",
            table_name=table_name,
            description=description,
            recommendation=recommendation,
            affected_data="Query performance and constraints"
        )
    
    def _analyze_engine_change(self, table_name: str, from_engine: str, to_engine: str) -> SafetyWarning:
        """Analyze storage engine change."""
        risk_factors = []
        risk_level = RiskLevel.MEDIUM
        
        # Specific engine change risks
        if from_engine.upper() == 'INNODB' and to_engine.upper() == 'MYISAM':
            risk_level = RiskLevel.HIGH
            risk_factors.append("Loss of transaction support")
            risk_factors.append("Loss of foreign key constraints")
            risk_factors.append("Loss of crash recovery")
        
        elif from_engine.upper() == 'MYISAM' and to_engine.upper() == 'INNODB':
            risk_level = RiskLevel.MEDIUM
            risk_factors.append("Table will be locked during conversion")
            risk_factors.append("Storage requirements may increase")
        
        description = f"Changing storage engine from {from_engine} to {to_engine}"
        if risk_factors:
            description += f": {'; '.join(risk_factors)}"
        
        return SafetyWarning(
            risk_level=risk_level,
            operation="CHANGE ENGINE",
            table_name=table_name,
            description=description,
            recommendation="Test thoroughly in staging environment",
            affected_data="Entire table will be rebuilt"
        )
    
    def _analyze_charset_change(self, table_name: str, from_charset: str, to_charset: str) -> SafetyWarning:
        """Analyze character set change."""
        # Check for potentially lossy charset conversions
        lossy_conversions = [
            ('utf8mb4', 'utf8'),
            ('utf8mb4', 'latin1'),
            ('utf8', 'latin1')
        ]
        
        if (from_charset, to_charset) in lossy_conversions:
            return SafetyWarning(
                risk_level=RiskLevel.HIGH,
                operation="CHANGE CHARSET",
                table_name=table_name,
                description=f"Character set change from {from_charset} to {to_charset} may cause data loss",
                recommendation="Verify all data can be represented in the target character set",
                affected_data="Text data may be corrupted or truncated"
            )
        
        return None
    
    def _extract_base_type(self, data_type: str) -> str:
        """Extract base data type from full type definition."""
        # Remove size specifications and return base type
        base_type = data_type.lower().split('(')[0]
        return base_type.strip()
    
    def _are_types_incompatible(self, from_type: str, to_type: str) -> bool:
        """Check if two data types are incompatible for conversion."""
        return (from_type, to_type) in self.incompatible_types
    
    def _is_size_reduction(self, from_type: str, to_type: str) -> bool:
        """Check if type change involves size reduction."""
        # Extract sizes from varchar, char, etc.
        def extract_size(type_str):
            import re
            match = re.search(r'\((\d+)\)', type_str)
            return int(match.group(1)) if match else None
        
        from_size = extract_size(from_type)
        to_size = extract_size(to_type)
        
        if from_size and to_size:
            return to_size < from_size
        
        return False
    
    def _get_modify_recommendation(self, risk_level: RiskLevel) -> str:
        """Get recommendation based on risk level."""
        if risk_level == RiskLevel.CRITICAL:
            return "CRITICAL: Backup data and test thoroughly. Consider data migration script."
        elif risk_level == RiskLevel.HIGH:
            return "HIGH RISK: Backup affected data and validate conversion in staging."
        elif risk_level == RiskLevel.MEDIUM:
            return "MEDIUM RISK: Test in staging environment before production."
        else:
            return "Review change and monitor for issues."
    
    def generate_safety_report(self, warnings: List[SafetyWarning]) -> str:
        """Generate a formatted safety report."""
        if not warnings:
            return "✅ No safety issues detected. Migration appears safe to execute."
        
        report_lines = [
            "🛡️  DDL Wizard Safety Analysis Report",
            "=" * 50,
            ""
        ]
        
        # Group by risk level
        by_risk = {}
        for warning in warnings:
            if warning.risk_level not in by_risk:
                by_risk[warning.risk_level] = []
            by_risk[warning.risk_level].append(warning)
        
        # Report in order of severity
        for risk_level in [RiskLevel.CRITICAL, RiskLevel.HIGH, RiskLevel.MEDIUM, RiskLevel.LOW]:
            if risk_level in by_risk:
                report_lines.append(f"{risk_level.value} RISK OPERATIONS:")
                report_lines.append("-" * 30)
                
                for warning in by_risk[risk_level]:
                    report_lines.append(f"Table: {warning.table_name}")
                    report_lines.append(f"Operation: {warning.operation}")
                    report_lines.append(f"Issue: {warning.description}")
                    report_lines.append(f"Recommendation: {warning.recommendation}")
                    if warning.affected_data:
                        report_lines.append(f"Affected Data: {warning.affected_data}")
                    report_lines.append("")
        
        # Summary
        critical_count = len(by_risk.get(RiskLevel.CRITICAL, []))
        high_count = len(by_risk.get(RiskLevel.HIGH, []))
        
        report_lines.append("SUMMARY:")
        report_lines.append(f"Total warnings: {len(warnings)}")
        report_lines.append(f"Critical issues: {critical_count}")
        report_lines.append(f"High risk issues: {high_count}")
        
        if critical_count > 0:
            report_lines.append("")
            report_lines.append("⚠️  CRITICAL ISSUES DETECTED!")
            report_lines.append("Review all critical issues before proceeding.")
        
        return "\n".join(report_lines)
