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
Data Loss Analyzer for DDL Wizard
Identifies migration operations that could result in data loss
"""

import logging
import re
from typing import Dict, List, Any, Set, Tuple
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class DataLossRisk(Enum):
    """Risk levels for data loss operations"""
    CRITICAL = "CRITICAL"  # Definite data loss
    HIGH = "HIGH"         # Likely data loss
    MEDIUM = "MEDIUM"     # Possible data loss
    LOW = "LOW"          # Minimal risk


@dataclass
class DataLossWarning:
    """Represents a potential data loss warning"""
    risk_level: DataLossRisk
    operation: str
    object_name: str
    object_type: str
    description: str
    impact: str
    mitigation: str
    sql_statement: str = ""


class DataLossAnalyzer:
    """Analyzes migration operations for potential data loss"""
    
    def __init__(self):
        self.warnings = []
        
        # Data type conversion risks
        self.risky_conversions = {
            ('VARCHAR', 'CHAR'): DataLossRisk.MEDIUM,
            ('TEXT', 'VARCHAR'): DataLossRisk.HIGH,
            ('LONGTEXT', 'TEXT'): DataLossRisk.HIGH,
            ('DECIMAL', 'INT'): DataLossRisk.HIGH,
            ('DOUBLE', 'FLOAT'): DataLossRisk.MEDIUM,
            ('DATETIME', 'DATE'): DataLossRisk.HIGH,
            ('TIMESTAMP', 'DATE'): DataLossRisk.HIGH,
            ('JSON', 'TEXT'): DataLossRisk.LOW,
            ('BLOB', 'VARBINARY'): DataLossRisk.MEDIUM,
        }
    
    def analyze_migration_sql(self, migration_sql: str, comparison_result: Dict[str, Any]) -> List[DataLossWarning]:
        """
        Analyze migration SQL for potential data loss operations
        
        Args:
            migration_sql: The generated migration SQL
            comparison_result: Schema comparison results
            
        Returns:
            List of data loss warnings
        """
        self.warnings = []
        
        # Analyze SQL statements
        self._analyze_sql_statements(migration_sql)
        
        # Analyze schema comparison results
        self._analyze_comparison_results(comparison_result)
        
        # Sort warnings by risk level
        self.warnings.sort(key=lambda w: list(DataLossRisk).index(w.risk_level))
        
        return self.warnings
    
    def _analyze_sql_statements(self, migration_sql: str):
        """Analyze individual SQL statements for data loss risks"""
        statements = self._parse_sql_statements(migration_sql)
        
        for statement in statements:
            statement = statement.strip()
            if not statement or statement.startswith('--'):
                continue
                
            # Check for various risky operations
            self._check_drop_operations(statement)
            self._check_column_modifications(statement)
            self._check_data_type_changes(statement)
            self._check_constraint_additions(statement)
            self._check_index_changes(statement)
    
    def _check_drop_operations(self, statement: str):
        """Check for DROP operations that cause data loss"""
        statement_upper = statement.upper()
        
        # DROP TABLE
        if re.match(r'DROP\s+TABLE', statement_upper):
            table_match = re.search(r'DROP\s+TABLE\s+(?:IF\s+EXISTS\s+)?[`"]?(\w+)[`"]?', statement_upper)
            if table_match:
                table_name = table_match.group(1)
                self.warnings.append(DataLossWarning(
                    risk_level=DataLossRisk.CRITICAL,
                    operation="DROP TABLE",
                    object_name=table_name,
                    object_type="TABLE",
                    description=f"Table '{table_name}' will be completely removed",
                    impact="ALL DATA in this table will be permanently lost",
                    mitigation="Export table data before migration, or exclude this operation",
                    sql_statement=statement
                ))
        
        # DROP COLUMN
        elif re.match(r'ALTER\s+TABLE.*DROP\s+COLUMN', statement_upper):
            table_match = re.search(r'ALTER\s+TABLE\s+[`"]?(\w+)[`"]?', statement_upper)
            column_match = re.search(r'DROP\s+COLUMN\s+[`"]?(\w+)[`"]?', statement_upper)
            if table_match and column_match:
                table_name = table_match.group(1)
                column_name = column_match.group(1)
                self.warnings.append(DataLossWarning(
                    risk_level=DataLossRisk.CRITICAL,
                    operation="DROP COLUMN",
                    object_name=f"{table_name}.{column_name}",
                    object_type="COLUMN",
                    description=f"Column '{column_name}' will be removed from table '{table_name}'",
                    impact="ALL DATA in this column will be permanently lost",
                    mitigation="Export column data before migration, or exclude this operation",
                    sql_statement=statement
                ))
        
        # DROP INDEX (low risk but worth noting)
        elif re.match(r'DROP\s+INDEX', statement_upper):
            index_match = re.search(r'DROP\s+INDEX\s+[`"]?(\w+)[`"]?', statement_upper)
            if index_match:
                index_name = index_match.group(1)
                self.warnings.append(DataLossWarning(
                    risk_level=DataLossRisk.LOW,
                    operation="DROP INDEX",
                    object_name=index_name,
                    object_type="INDEX",
                    description=f"Index '{index_name}' will be removed",
                    impact="Query performance may be affected, no data loss",
                    mitigation="Monitor query performance after migration",
                    sql_statement=statement
                ))
    
    def _check_column_modifications(self, statement: str):
        """Check for column modifications that might cause data loss"""
        statement_upper = statement.upper()
        
        # MODIFY COLUMN with size reduction
        if re.match(r'ALTER\s+TABLE.*MODIFY\s+COLUMN', statement_upper):
            table_match = re.search(r'ALTER\s+TABLE\s+[`"]?(\w+)[`"]?', statement_upper)
            column_match = re.search(r'MODIFY\s+COLUMN\s+[`"]?(\w+)[`"]?\s+(\w+(?:\(\d+(?:,\d+)?\))?)', statement_upper)
            
            if table_match and column_match:
                table_name = table_match.group(1)
                column_name = column_match.group(1)
                new_type = column_match.group(2)
                
                # Check for size reductions
                if self._is_size_reduction(new_type):
                    self.warnings.append(DataLossWarning(
                        risk_level=DataLossRisk.HIGH,
                        operation="MODIFY COLUMN",
                        object_name=f"{table_name}.{column_name}",
                        object_type="COLUMN",
                        description=f"Column '{column_name}' type changed to '{new_type}' (potential size reduction)",
                        impact="Data truncation may occur if existing data exceeds new size limits",
                        mitigation="Verify all existing data fits within new size constraints",
                        sql_statement=statement
                    ))
        
        # Adding NOT NULL constraint
        elif re.match(r'ALTER\s+TABLE.*MODIFY\s+COLUMN.*NOT\s+NULL', statement_upper):
            table_match = re.search(r'ALTER\s+TABLE\s+[`"]?(\w+)[`"]?', statement_upper)
            column_match = re.search(r'MODIFY\s+COLUMN\s+[`"]?(\w+)[`"]?', statement_upper)
            
            if table_match and column_match:
                table_name = table_match.group(1)
                column_name = column_match.group(1)
                self.warnings.append(DataLossWarning(
                    risk_level=DataLossRisk.HIGH,
                    operation="ADD NOT NULL CONSTRAINT",
                    object_name=f"{table_name}.{column_name}",
                    object_type="COLUMN",
                    description=f"Column '{column_name}' will require non-null values",
                    impact="Migration will fail if any existing rows have NULL values in this column",
                    mitigation="Update NULL values before migration or provide DEFAULT value",
                    sql_statement=statement
                ))
    
    def _check_data_type_changes(self, statement: str):
        """Check for data type conversions that might cause data loss"""
        statement_upper = statement.upper()
        
        # Look for MODIFY COLUMN with type changes
        modify_match = re.search(
            r'ALTER\s+TABLE\s+[`"]?(\w+)[`"]?.*MODIFY\s+COLUMN\s+[`"]?(\w+)[`"]?\s+(\w+)(?:\(\d+(?:,\d+)?\))?',
            statement_upper
        )
        
        if modify_match:
            table_name = modify_match.group(1)
            column_name = modify_match.group(2)
            new_type = modify_match.group(3)
            
            # This would require knowing the original type to determine risk
            # For now, flag common risky conversions
            if new_type in ['INT', 'SMALLINT', 'TINYINT'] and 'DECIMAL' in statement_upper:
                self.warnings.append(DataLossWarning(
                    risk_level=DataLossRisk.HIGH,
                    operation="DATA TYPE CONVERSION",
                    object_name=f"{table_name}.{column_name}",
                    object_type="COLUMN",
                    description=f"Converting to {new_type} from decimal type",
                    impact="Decimal precision will be lost",
                    mitigation="Verify data conversion is acceptable for your use case",
                    sql_statement=statement
                ))
    
    def _check_constraint_additions(self, statement: str):
        """Check for constraint additions that might cause data loss"""
        statement_upper = statement.upper()
        
        # Adding UNIQUE constraint
        if re.match(r'ALTER\s+TABLE.*ADD.*UNIQUE', statement_upper):
            table_match = re.search(r'ALTER\s+TABLE\s+[`"]?(\w+)[`"]?', statement_upper)
            if table_match:
                table_name = table_match.group(1)
                self.warnings.append(DataLossWarning(
                    risk_level=DataLossRisk.MEDIUM,
                    operation="ADD UNIQUE CONSTRAINT",
                    object_name=table_name,
                    object_type="CONSTRAINT",
                    description="Adding UNIQUE constraint to table",
                    impact="Migration will fail if duplicate values exist",
                    mitigation="Remove duplicate values before migration",
                    sql_statement=statement
                ))
        
        # Adding CHECK constraint
        elif re.match(r'ALTER\s+TABLE.*ADD.*CHECK', statement_upper):
            table_match = re.search(r'ALTER\s+TABLE\s+[`"]?(\w+)[`"]?', statement_upper)
            if table_match:
                table_name = table_match.group(1)
                self.warnings.append(DataLossWarning(
                    risk_level=DataLossRisk.MEDIUM,
                    operation="ADD CHECK CONSTRAINT",
                    object_name=table_name,
                    object_type="CONSTRAINT",
                    description="Adding CHECK constraint to table",
                    impact="Migration will fail if existing data violates the constraint",
                    mitigation="Verify all existing data meets the constraint requirements",
                    sql_statement=statement
                ))
    
    def _check_index_changes(self, statement: str):
        """Check for index changes that affect performance"""
        statement_upper = statement.upper()
        
        # Dropping primary key
        if re.match(r'ALTER\s+TABLE.*DROP\s+PRIMARY\s+KEY', statement_upper):
            table_match = re.search(r'ALTER\s+TABLE\s+[`"]?(\w+)[`"]?', statement_upper)
            if table_match:
                table_name = table_match.group(1)
                self.warnings.append(DataLossWarning(
                    risk_level=DataLossRisk.MEDIUM,
                    operation="DROP PRIMARY KEY",
                    object_name=table_name,
                    object_type="CONSTRAINT",
                    description="Primary key will be removed",
                    impact="Table will lose uniqueness guarantee and replication may be affected",
                    mitigation="Ensure this is intentional and consider replication implications",
                    sql_statement=statement
                ))
    
    def _analyze_comparison_results(self, comparison_result: Dict[str, Any]):
        """Analyze schema comparison results for data loss risks"""
        
        # Check for tables only in destination (will be dropped)
        for object_type in ['tables', 'views']:
            if object_type in comparison_result:
                only_in_dest = comparison_result[object_type].get('only_in_dest', [])
                for obj_name in only_in_dest:
                    self.warnings.append(DataLossWarning(
                        risk_level=DataLossRisk.CRITICAL,
                        operation=f"DROP {object_type.upper()[:-1]}",
                        object_name=obj_name,
                        object_type=object_type.upper()[:-1],
                        description=f"{object_type[:-1].title()} '{obj_name}' exists only in destination",
                        impact=f"This {object_type[:-1]} and all its data will be removed",
                        mitigation=f"Export {object_type[:-1]} structure and data before migration",
                        sql_statement=""
                    ))
        
        # Check for column differences that might indicate drops
        if 'tables' in comparison_result:
            in_both = comparison_result['tables'].get('in_both', [])
            for table_name in in_both:
                # This would require more detailed column comparison
                # For now, we flag this as needing manual review
                pass
    
    def _is_size_reduction(self, new_type: str) -> bool:
        """Check if a type change represents a size reduction"""
        # Simple heuristic - look for small size specifications
        size_match = re.search(r'\((\d+)\)', new_type)
        if size_match:
            size = int(size_match.group(1))
            # Flag as potential reduction if size is "small"
            if 'VARCHAR' in new_type.upper() and size < 100:
                return True
            if 'CHAR' in new_type.upper() and size < 50:
                return True
        return False
    
    def _parse_sql_statements(self, sql_content: str) -> List[str]:
        """Parse SQL content into individual statements"""
        # Simple parsing - split on semicolons not in quotes
        statements = []
        current_statement = ""
        in_quotes = False
        quote_char = None
        
        for char in sql_content:
            if not in_quotes and char in ['"', "'", '`']:
                in_quotes = True
                quote_char = char
            elif in_quotes and char == quote_char:
                in_quotes = False
                quote_char = None
            elif not in_quotes and char == ';':
                if current_statement.strip():
                    statements.append(current_statement.strip())
                current_statement = ""
                continue
            
            current_statement += char
        
        if current_statement.strip():
            statements.append(current_statement.strip())
        
        return statements
    
    def generate_report(self) -> str:
        """Generate a formatted data loss analysis report"""
        if not self.warnings:
            return "✅ No potential data loss operations detected."
        
        report = []
        report.append("⚠️  DATA LOSS ANALYSIS REPORT")
        report.append("=" * 50)
        report.append("")
        
        # Group by risk level
        by_risk = {}
        for warning in self.warnings:
            if warning.risk_level not in by_risk:
                by_risk[warning.risk_level] = []
            by_risk[warning.risk_level].append(warning)
        
        # Risk level icons and descriptions
        risk_icons = {
            DataLossRisk.CRITICAL: "🚨",
            DataLossRisk.HIGH: "⚠️ ",
            DataLossRisk.MEDIUM: "⚡",
            DataLossRisk.LOW: "ℹ️ "
        }
        
        for risk_level in [DataLossRisk.CRITICAL, DataLossRisk.HIGH, DataLossRisk.MEDIUM, DataLossRisk.LOW]:
            if risk_level in by_risk:
                warnings = by_risk[risk_level]
                icon = risk_icons[risk_level]
                
                report.append(f"{icon} {risk_level.value} RISK ({len(warnings)} operations)")
                report.append("-" * 40)
                
                for i, warning in enumerate(warnings, 1):
                    report.append(f"{i}. {warning.operation}: {warning.object_name}")
                    report.append(f"   Type: {warning.object_type}")
                    report.append(f"   Description: {warning.description}")
                    report.append(f"   Impact: {warning.impact}")
                    report.append(f"   Mitigation: {warning.mitigation}")
                    if warning.sql_statement:
                        report.append(f"   SQL: {warning.sql_statement[:100]}...")
                    report.append("")
                
                report.append("")
        
        # Summary
        total_warnings = len(self.warnings)
        critical_count = len(by_risk.get(DataLossRisk.CRITICAL, []))
        high_count = len(by_risk.get(DataLossRisk.HIGH, []))
        
        report.append("📊 SUMMARY")
        report.append("-" * 20)
        report.append(f"Total warnings: {total_warnings}")
        report.append(f"Critical risks: {critical_count}")
        report.append(f"High risks: {high_count}")
        
        if critical_count > 0:
            report.append("")
            report.append("🛑 RECOMMENDATION: Do not proceed without reviewing critical risks!")
        elif high_count > 0:
            report.append("")
            report.append("⚠️  RECOMMENDATION: Carefully review high-risk operations before proceeding.")
        
        return "\n".join(report)
