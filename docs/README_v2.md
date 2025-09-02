# DDL Wizard v2.0 - Database Schema Migration Tool

DDL Wizard is a comprehensive database schema migration tool that provides both CLI and GUI interfaces for comparing database schemas, generating migration scripts, and managing database changes safely.

## 🚀 New in Version 2.0

- **🖥️ Modern Streamlit GUI** - Web-based interface for easy database migrations
- **🏗️ Refactored Architecture** - Clean separation between CLI and GUI using shared core
- **🔧 Enhanced Core Module** - Reusable functionality for both interfaces
- **🛡️ Improved Safety Analysis** - Better validation and rollback generation
- **📊 Rich Visualizations** - Schema documentation and migration reports
- **🔄 Git Integration** - Version control for migration tracking

## 📋 Features

### Core Functionality
- **Schema Comparison**: Compare tables, procedures, functions, triggers, and events
- **Migration Generation**: Create SQL scripts to synchronize schemas
- **Rollback Scripts**: Generate safe rollback SQL for all changes
- **Safety Analysis**: Detect potentially dangerous operations
- **DELIMITER Support**: Proper handling of stored procedures/functions/triggers
- **Migration History**: Track all migrations with detailed logs

### Interfaces
- **CLI Interface**: Professional command-line tool for automation and CI/CD
- **GUI Interface**: User-friendly web interface for interactive use
- **Both interfaces use the same core logic ensuring consistency**

## 🛠️ Installation

### Prerequisites
- Python 3.8+
- MySQL/MariaDB database access
- Git (for version control features)

### Setup
```bash
# Clone the repository
git clone <repository-url>
cd ddlwizard

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\\Scripts\\activate

# Install dependencies
pip install -r requirements.txt

# Verify installation
python main.py --help
```

### Project Structure (v1.1.0+)
```
ddlwizard/
├── ddlwizard/              # Main package
│   ├── cli.py              # Command line interface
│   ├── core.py             # Core business logic
│   ├── gui.py              # Streamlit web interface
│   └── utils/              # Organized utilities
├── testdata/               # 🧪 Sample test schemas
│   ├── source_schema.sql   # Source test database
│   ├── destination_schema.sql # Destination test database
│   ├── README.md           # Test setup instructions
│   └── validate_setup.sh   # Validation script
├── tests/                  # Test suite
├── docs/                   # Documentation
├── scripts/                # Utility scripts
├── config/                 # Configuration files
├── pyproject.toml          # Modern Python packaging
└── main.py                 # Backward compatibility entry point
```

### Dependencies
```
PyMySQL>=1.0.2
pyyaml>=6.0
python-dotenv>=0.19.0
streamlit>=1.28.0
plotly>=5.15.0
pandas>=1.5.0
```

## 🖥️ GUI Usage

### Starting the GUI
```bash
streamlit run ddl_wizard_gui.py
```

Then open your browser to `http://localhost:8501`

### GUI Features
- **📊 Interactive Forms**: Easy database configuration
- **🔍 Connection Testing**: Validate database connections before migration
- **⚙️ Migration Settings**: Configure output directory and options
- **📈 Progress Tracking**: Real-time migration progress
- **📥 File Downloads**: Download migration SQL, rollback scripts, and reports
- **🎨 Syntax Highlighting**: SQL code display with highlighting
- **⚠️ Safety Warnings**: Visual display of potential issues

### GUI Workflow
1. **Configure Source Database**: Enter connection details and test
2. **Configure Destination Database**: Enter connection details and test  
3. **Set Migration Options**: Choose output directory and settings
4. **Run Migration Analysis**: Generate migration files
5. **Review Results**: Download files and review safety warnings
6. **Apply Changes**: Use generated SQL in your database

## 💻 CLI Usage

### Basic Commands

#### Compare Schemas (Main Operation)
```bash
# Compare two databases and generate migration
python main.py compare \
  --source-host localhost --source-user root --source-schema db1 \
  --dest-host localhost --dest-user root --dest-schema db2
```

#### Extract DDL from Database
```bash
python main.py extract \
  --source-host localhost --source-user root --source-schema mydb
```

#### Generate Schema Visualizations
```bash
python main.py visualize \
  --source-host localhost --source-user root --source-schema mydb
```

#### Show Migration History
```bash
python main.py history --limit 10
```

### Configuration File
Create `config.yaml`:
```yaml
source:
  host: localhost
  port: 3306
  user: root
  password: secret
  schema: source_db

destination:
  host: localhost
  port: 3306
  user: root
  password: secret
  schema: dest_db

safety:
  validate_before_execution: true
  allow_data_loss_operations: false

output:
  output_dir: ./ddl_output
  migration_file: migration.sql
  rollback_file: rollback.sql
```

Use with:
```bash
python main.py compare --config config/ddl_wizard_config.yaml
```

### CLI Options
```bash
# Global options
--verbose, -v          Enable verbose logging
--config FILE          Configuration file path
--profile PROFILE      Configuration profile to use
--output-dir DIR       Output directory (default: ./ddl_output)

# Compare mode options
--skip-safety-checks   Skip safety analysis
--enable-visualization Generate schema visualizations
--interactive          Enable interactive confirmation
--auto-approve         Auto-approve migrations
--dry-run              Generate files without executing
```

## 🏗️ Architecture

### Core Module (`ddl_wizard_core.py`)
The heart of DDL Wizard containing reusable business logic:
- **DDLWizardCore**: Main class with core functionality
- **run_complete_migration()**: High-level workflow function
- Database connection management
- Schema extraction and comparison
- Migration SQL generation
- Rollback SQL generation
- Safety analysis
- Migration reporting

### CLI Interface
Professional command-line interface:
- Argument parsing and validation
- Configuration management
- Calls core module for operations
- Output formatting and logging

### GUI Interface
Modern web-based interface using Streamlit:

**Starting the GUI:**
```bash
# Recommended method
streamlit run ddlwizard/gui.py --server.port 8501

# Alternative entry point
streamlit run gui_main.py --server.port 8501

# Legacy compatibility
streamlit run ddl_wizard_gui.py --server.port 8501
```

**Features:**
- Interactive forms and controls
- Real-time validation and feedback
- Progress indicators
- File download capabilities
- Calls same core module as CLI
- Visual schema comparison
- Migration preview and execution controls

### Supporting Modules
- **database.py**: Database connection and DDL extraction
- **config_manager.py**: Configuration file handling
- **schema_comparator.py**: Schema comparison logic
- **safety_analyzer.py**: Safety validation
- **migration_history.py**: Migration tracking
- **schema_visualizer.py**: Documentation generation

## 📁 Output Files

DDL Wizard generates several files in the output directory:

### Core Files
- **migration.sql**: SQL script to migrate destination to match source
- **rollback.sql**: SQL script to rollback changes
- **migration_report.md**: Detailed migration report

### Documentation (if enabled)
- **documentation/schema_documentation.html**: Interactive schema docs
- **documentation/schema_erd.dot**: Entity relationship diagram
- **documentation/schema_structure.json**: Schema metadata

### Organized Structure
```
ddl_output/
├── migration.sql
├── rollback.sql
├── migration_report.md
├── comparison_report.txt
├── documentation/
│   ├── schema_documentation.html
│   ├── schema_erd.dot
│   └── schema_structure.json
├── tables/
├── procedures/
├── functions/
├── triggers/
└── events/
```

## 🛡️ Safety Features

### Safety Analysis
- **Data Loss Detection**: Identifies operations that may lose data
- **Dependency Analysis**: Checks object dependencies
- **Constraint Validation**: Validates foreign key constraints
- **Permission Checks**: Verifies required permissions

### Safety Levels
- **HIGH**: Critical issues that could cause data loss
- **MEDIUM**: Operations requiring careful review
- **LOW**: Informational warnings

### Rollback Support
- **Automatic Generation**: Rollback scripts for all changes
- **DELIMITER Handling**: Proper syntax for stored objects
- **Dependency Order**: Correct rollback order based on dependencies

## 🔄 Version Control Integration

### Git Features
- **Automatic Repository**: Creates git repo in output directory
- **DDL Tracking**: Commits DDL objects for both databases
- **Change History**: Full history of schema changes
- **Branch Support**: Separate branches for different migrations

### Workflow Integration
```bash
# Tag stable version before developing GUI
git tag -a v1.0.0 -m "Stable CLI version"

# Create feature branch for new development
git checkout -b feature/new-feature

# DDL Wizard automatically commits changes
python main.py compare --source-host ... --dest-host ...
```

## 📊 Migration Reports

### Detailed Reports Include
- **Schema Summary**: Overview of changes
- **Operation Details**: Specific DDL statements
- **Safety Analysis**: Warnings and recommendations
- **Execution Statistics**: Performance metrics
- **Rollback Instructions**: How to revert changes

### Report Formats
- **Markdown**: Human-readable migration reports
- **JSON**: Machine-readable schema metadata
- **HTML**: Interactive documentation with visualizations

## 🔧 Development

### Architecture Benefits
- **Separation of Concerns**: Clear boundaries between CLI, GUI, and core
- **Reusability**: Core logic shared between interfaces
- **Testability**: Each component can be tested independently
- **Maintainability**: Changes in core affect both interfaces consistently

### Adding New Features
1. **Core Logic**: Add functionality to `ddl_wizard_core.py`
2. **CLI Integration**: Add CLI arguments and commands
3. **GUI Integration**: Add Streamlit controls and displays
4. **Testing**: Update test suite for all interfaces

### Testing
```bash
# Run comprehensive test suite
python ddl_wizard_testsuite.py

# Run with specific database connections
python ddl_wizard_testsuite.py --host localhost --port 3306 --user root --password secret

# Test specific functionality
python -m pytest tests/
```

### Test Data Preservation
The test suite automatically saves all generated SQL scripts and test results to organized directories under `test_data/` for reference, then cleans up temporary files:

```
test_data/
└── ddlw-test-20250902_115230/
    ├── test_summary.txt              # Test run summary
    ├── ddl_wizard_test.log           # Detailed test log
    ├── test_output/                  # Original test directory names
    ├── test_output_post_migration/   # (for direct reference)
    ├── test_output_final/            # 
    ├── ddl-wizard-testsuite-initial-migration-20250902_115230/
    │   ├── migration.sql             # Generated migration script
    │   ├── rollback.sql              # Generated rollback script
    │   ├── migration_report.md       # Detailed migration report
    │   └── comparison_report.txt     # Schema comparison details
    ├── ddl-wizard-testsuite-post-migration-verification-20250902_115230/
    │   ├── migration.sql             # Post-migration verification files
    │   ├── rollback.sql              # (should be minimal/empty)
    │   └── migration_report.md       # Post-migration analysis
    └── ddl-wizard-testsuite-rollback-verification-20250902_115230/
        ├── migration.sql             # Final verification files  
        ├── rollback.sql              # (should match initial state)
        └── migration_report.md       # Rollback verification results
```

**Cleanup Process**: After preserving all test data, temporary `test_output*` directories are automatically removed from the working directory to keep it clean.

Each test run gets its own main directory (`ddlw-test-<timestamp>`) containing:
- **Main Directory**: Contains test summary and log files for the entire run
- **Original Test Directories**: Preserved with their original names (`test_output*`) for direct reference
- **Descriptive Test Directories**: Renamed with clear phase descriptions for better organization
  - **initial-migration**: Original migration generation and analysis
  - **post-migration-verification**: Files generated after applying migration
  - **rollback-verification**: Files generated after applying rollback

This preserved test data allows you to:
- **Review Generated SQL**: Examine migration and rollback scripts for each phase
- **Analyze Test Results**: Debug failed tests and understand schema changes at each step
- **Reference Examples**: Use as templates for manual migrations
- **Track Changes**: Compare different test runs and phases over time
- **Understand Workflow**: See exactly what happens at each stage of the migration cycle
- **Organized Analysis**: All files from a single test run are grouped together
- **Direct Access**: Use original directory names for familiar navigation
- **Clean Workspace**: Temporary directories are cleaned up after each run

## 🤝 Contributing

1. **Fork the repository**
2. **Create feature branch**: `git checkout -b feature/amazing-feature`
3. **Make changes**: Follow existing code patterns
4. **Add tests**: Ensure new functionality is tested
5. **Update documentation**: Keep README and docs current
6. **Submit pull request**: Describe changes and benefits

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

### Getting Help
- **GitHub Issues**: Report bugs and request features
- **Documentation**: Check this README and inline documentation
- **Examples**: See `test_data/` directory for sample configurations

### Common Issues
- **Connection Errors**: Check database credentials and network access
- **Permission Errors**: Ensure user has required database permissions
- **DELIMITER Issues**: Usually resolved automatically by DDL Wizard
- **Large Schemas**: Consider using filters or splitting operations

## 🎉 Acknowledgments

- **MySQL/MariaDB**: For excellent database technology
- **Streamlit**: For making beautiful web apps easy
- **PyMySQL**: For reliable database connectivity
- **Community**: For feedback and contributions

---

**DDL Wizard v2.0** - Making database migrations safer and easier! 🧙‍♂️✨
