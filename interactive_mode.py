"""
Interactive mode and user interface for DDL Wizard.
Provides safe user interaction and confirmation prompts.
"""

import sys
import logging
from typing import List, Dict, Any, Optional
from enum import Enum
from safety_analyzer import SafetyWarning, RiskLevel

logger = logging.getLogger(__name__)


class UserResponse(Enum):
    """User response options."""
    YES = "yes"
    NO = "no"
    ABORT = "abort"
    SKIP = "skip"
    VIEW_DETAILS = "details"


class InteractiveMode:
    """Handles interactive user prompts and confirmations."""
    
    def __init__(self, enable_colors: bool = True):
        self.enable_colors = enable_colors
        self.colors = {
            'red': '\033[91m' if enable_colors else '',
            'green': '\033[92m' if enable_colors else '',
            'yellow': '\033[93m' if enable_colors else '',
            'blue': '\033[94m' if enable_colors else '',
            'magenta': '\033[95m' if enable_colors else '',
            'cyan': '\033[96m' if enable_colors else '',
            'white': '\033[97m' if enable_colors else '',
            'bold': '\033[1m' if enable_colors else '',
            'end': '\033[0m' if enable_colors else ''
        }
    
    def colorize(self, text: str, color: str) -> str:
        """Apply color to text if colors are enabled."""
        return f"{self.colors.get(color, '')}{text}{self.colors['end']}"
    
    def print_header(self, title: str):
        """Print a formatted header."""
        print(f"\n{self.colorize('=' * 60, 'cyan')}")
        print(f"{self.colorize(title.center(60), 'bold')}")
        print(f"{self.colorize('=' * 60, 'cyan')}\n")
    
    def print_warning(self, message: str):
        """Print a warning message."""
        print(f"{self.colorize('⚠️  WARNING:', 'yellow')} {message}")
    
    def print_error(self, message: str):
        """Print an error message."""
        print(f"{self.colorize('❌ ERROR:', 'red')} {message}")
    
    def print_success(self, message: str):
        """Print a success message."""
        print(f"{self.colorize('✅ SUCCESS:', 'green')} {message}")
    
    def print_info(self, message: str):
        """Print an info message."""
        print(f"{self.colorize('ℹ️  INFO:', 'blue')} {message}")
    
    def confirm_migration(self, source_schema: str, dest_schema: str, 
                         operation_count: int, safety_warnings: List[SafetyWarning]) -> bool:
        """Confirm if user wants to proceed with migration."""
        self.print_header("Migration Confirmation")
        
        print(f"Source Schema: {self.colorize(source_schema, 'cyan')}")
        print(f"Destination Schema: {self.colorize(dest_schema, 'cyan')}")
        print(f"Total Operations: {self.colorize(str(operation_count), 'white')}")
        
        # Show safety summary
        if safety_warnings:
            critical_count = sum(1 for w in safety_warnings if w.risk_level == RiskLevel.CRITICAL)
            high_count = sum(1 for w in safety_warnings if w.risk_level == RiskLevel.HIGH)
            
            if critical_count > 0:
                self.print_error(f"{critical_count} CRITICAL safety issues detected!")
            if high_count > 0:
                self.print_warning(f"{high_count} HIGH RISK safety issues detected!")
            
            print(f"\nTo see detailed safety analysis, type 'details'")
        else:
            self.print_success("No safety issues detected")
        
        print(f"\n{self.colorize('Options:', 'bold')}")
        print("  yes     - Proceed with migration")
        print("  no      - Cancel migration")
        print("  details - View detailed safety analysis")
        print("  abort   - Exit DDL Wizard")
        
        while True:
            response = input(f"\n{self.colorize('Proceed with migration?', 'bold')} [yes/no/details/abort]: ").strip().lower()
            
            if response in ['y', 'yes']:
                return True
            elif response in ['n', 'no']:
                print("Migration cancelled by user.")
                return False
            elif response == 'details':
                self._show_safety_details(safety_warnings)
                continue
            elif response == 'abort':
                print("Aborting DDL Wizard.")
                sys.exit(0)
            else:
                print(f"{self.colorize('Invalid response.', 'red')} Please enter yes, no, details, or abort.")
    
    def confirm_dangerous_operation(self, operation: str, table_name: str, warning: SafetyWarning) -> bool:
        """Confirm a specific dangerous operation."""
        print(f"\n{self.colorize('⚠️  DANGEROUS OPERATION DETECTED', 'red')}")
        print(f"Table: {self.colorize(table_name, 'cyan')}")
        print(f"Operation: {self.colorize(operation, 'yellow')}")
        print(f"Risk Level: {self.colorize(warning.risk_level.value, 'red')}")
        print(f"Issue: {warning.description}")
        print(f"Recommendation: {warning.recommendation}")
        
        if warning.affected_data:
            print(f"Affected Data: {self.colorize(warning.affected_data, 'red')}")
        
        while True:
            response = input(f"\n{self.colorize('Continue with this operation?', 'bold')} [yes/no/skip/abort]: ").strip().lower()
            
            if response in ['y', 'yes']:
                return True
            elif response in ['n', 'no', 's', 'skip']:
                print(f"Skipping operation: {operation}")
                return False
            elif response == 'abort':
                print("Aborting migration.")
                sys.exit(0)
            else:
                print(f"{self.colorize('Invalid response.', 'red')} Please enter yes, no, skip, or abort.")
    
    def _show_safety_details(self, warnings: List[SafetyWarning]):
        """Display detailed safety analysis."""
        if not warnings:
            self.print_success("No safety issues found.")
            return
        
        self.print_header("Detailed Safety Analysis")
        
        # Group by risk level
        by_risk = {}
        for warning in warnings:
            if warning.risk_level not in by_risk:
                by_risk[warning.risk_level] = []
            by_risk[warning.risk_level].append(warning)
        
        # Display by risk level
        for risk_level in [RiskLevel.CRITICAL, RiskLevel.HIGH, RiskLevel.MEDIUM, RiskLevel.LOW]:
            if risk_level in by_risk:
                color = {
                    RiskLevel.CRITICAL: 'red',
                    RiskLevel.HIGH: 'yellow', 
                    RiskLevel.MEDIUM: 'blue',
                    RiskLevel.LOW: 'green'
                }[risk_level]
                
                print(f"\n{self.colorize(f'{risk_level.value} RISK OPERATIONS:', color)}")
                print(f"{self.colorize('-' * 40, color)}")
                
                for i, warning in enumerate(by_risk[risk_level], 1):
                    print(f"\n{self.colorize(f'{i}.', 'white')} Table: {self.colorize(warning.table_name, 'cyan')}")
                    print(f"   Operation: {warning.operation}")
                    print(f"   Issue: {warning.description}")
                    print(f"   Recommendation: {warning.recommendation}")
                    if warning.affected_data:
                        print(f"   Affected Data: {self.colorize(warning.affected_data, 'red')}")
        
        print("\n" + "=" * 60)
    
    def show_migration_progress(self, current: int, total: int, operation: str):
        """Show migration progress."""
        percentage = (current / total) * 100 if total > 0 else 0
        bar_length = 40
        filled_length = int(bar_length * current // total) if total > 0 else 0
        
        bar = '█' * filled_length + '-' * (bar_length - filled_length)
        
        print(f"\r{self.colorize('Progress:', 'blue')} |{bar}| {percentage:.1f}% ({current}/{total}) - {operation}", end='', flush=True)
        
        if current == total:
            print()  # New line when complete
    
    def display_migration_summary(self, results: Dict[str, Any]):
        """Display migration execution summary."""
        self.print_header("Migration Summary")
        
        success_count = results.get('successful_operations', 0)
        failed_count = results.get('failed_operations', 0)
        skipped_count = results.get('skipped_operations', 0)
        total_time = results.get('execution_time', 0)
        
        print(f"Successful Operations: {self.colorize(str(success_count), 'green')}")
        print(f"Failed Operations: {self.colorize(str(failed_count), 'red' if failed_count > 0 else 'green')}")
        print(f"Skipped Operations: {self.colorize(str(skipped_count), 'yellow' if skipped_count > 0 else 'green')}")
        print(f"Total Execution Time: {self.colorize(f'{total_time:.2f}s', 'blue')}")
        
        if failed_count > 0:
            self.print_error("Some operations failed. Check the logs for details.")
            print(f"Failed operations logged to: {results.get('error_log', 'migration_errors.log')}")
        else:
            self.print_success("All operations completed successfully!")
        
        if results.get('rollback_script'):
            print(f"\nRollback script available: {self.colorize(results['rollback_script'], 'cyan')}")
    
    def prompt_for_backup(self, tables: List[str]) -> bool:
        """Prompt user to create backups before migration."""
        if not tables:
            return True
        
        self.print_warning("The following tables will be modified and should be backed up:")
        for table in tables:
            print(f"  • {self.colorize(table, 'cyan')}")
        
        print(f"\n{self.colorize('Backup Options:', 'bold')}")
        print("  1. I have already created backups")
        print("  2. Skip backup (NOT RECOMMENDED)")
        print("  3. Cancel migration to create backups")
        
        while True:
            response = input(f"\n{self.colorize('Choose an option [1-3]:', 'bold')} ").strip()
            
            if response == '1':
                self.print_success("Proceeding with migration (backups confirmed)")
                return True
            elif response == '2':
                self.print_warning("Proceeding WITHOUT backups (high risk!)")
                confirm = input(f"{self.colorize('Are you absolutely sure? [yes/no]:', 'red')} ").strip().lower()
                if confirm in ['y', 'yes']:
                    return True
                continue
            elif response == '3':
                print("Please create backups and restart the migration.")
                return False
            else:
                print(f"{self.colorize('Invalid option.', 'red')} Please choose 1, 2, or 3.")
    
    def display_dry_run_results(self, operations: List[Dict[str, Any]]):
        """Display dry run results."""
        self.print_header("Dry Run Results")
        
        print(f"Total operations that would be executed: {self.colorize(str(len(operations)), 'cyan')}")
        print("\nOperations preview:")
        
        for i, op in enumerate(operations[:10], 1):  # Show first 10 operations
            op_type = op.get('operation_type', 'UNKNOWN')
            table_name = op.get('table_name', 'N/A')
            description = op.get('description', op.get('sql', ''))[:60]
            
            print(f"  {i:2d}. {self.colorize(op_type, 'yellow'):10} {self.colorize(table_name, 'cyan'):20} {description}...")
        
        if len(operations) > 10:
            print(f"  ... and {len(operations) - 10} more operations")
        
        print(f"\n{self.colorize('DRY RUN COMPLETE', 'green')} - No changes were made to the database.")
        print("Review the generated migration files and run without --dry-run to execute.")
