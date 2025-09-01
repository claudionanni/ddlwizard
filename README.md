# 🧙‍♂️ DDL Wizard - MariaDB Schema Management Tool

A comprehensive Python tool for MariaDB/MySQL schema management, version control, and automated migration generation. DDL Wizard provides professional-grade features for safe, reliable database schema evolution.

## 🚀 Features

### Core Functionality
- **Schema Extraction**: Extract DDL objects (tables, functions, triggers, stored procedures, events) from MariaDB/MySQL databases
- **Version Control**: Git-based version control for database objects
- **Schema Comparison**: Deep structural comparison between source and destination schemas
- **Migration Generation**: Automated ALTER statement generation with dependency ordering
- **Rollback Support**: Generate rollback scripts for safe migration reversals

### Advanced Features
- **Safety Analysis**: Detect data loss scenarios and risky operations
- **Dependency Management**: Analyze foreign key relationships and order operations correctly
- **Interactive Mode**: User-friendly prompts with colored output and progress tracking
- **Configuration Management**: YAML-based configuration with environment variable support
- **Migration History**: SQLite-based tracking of all migration executions
- **Schema Visualization**: Generate ER diagrams and documentation (Mermaid, Graphviz, HTML)
- **Multiple Operation Modes**: Extract, compare, migrate, visualize, and history modes

## 📋 Requirements

- Python 3.8+
- MariaDB or MySQL database access
- Git (for version control features)

## 🛠 Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd ddlwizard
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Verify installation:
```bash
python main.py --help
```

## 🎯 Quick Start

### Basic Schema Comparison
Compare two schemas and generate migration SQL:

```bash
python main.py 
  --source-host localhost --source-user root --source-password password --source-schema source_db 
  --dest-host localhost --dest-user root --dest-password password --dest-schema dest_db 
  --output-dir ./migration_output
```

### Using Configuration Files
Create a configuration file (`config.yaml`) and use profiles:

```bash
python main.py --config ddl_wizard_config.yaml --profile development
```

### Interactive Mode
Enable interactive mode for user confirmations:

```bash
python main.py --interactive 
  --source-host localhost --source-user root --source-password password --source-schema source_db 
  --dest-host localhost --dest-user root --dest-password password --dest-schema dest_db
```

## 🔧 Operation Modes

### Compare Mode (Default)
Compares schemas and generates migration SQL:
```bash
python main.py --mode compare [database options]
```

### Extract Mode
Extracts DDL objects from source database only:
```bash
python main.py --mode extract --source-host HOST --source-user USER --source-password PASS --source-schema SCHEMA
```

### Visualize Mode
Generates schema documentation and ER diagrams:
```bash
python main.py --mode visualize --source-host HOST --source-user USER --source-password PASS --source-schema SCHEMA
```

### History Mode
Shows migration execution history:
```bash
python main.py --mode history
```

## 📁 Configuration

DDL Wizard supports YAML configuration files with multiple profiles:

```yaml
default:
  source_database:
    host: "localhost"
    port: 3306
    user: "${DB_USER}"
    password: "${DB_PASSWORD}"
    schema: "source_schema"
  
  destination_database:
    host: "localhost"
    port: 3306
    user: "${DB_USER}"
    password: "${DB_PASSWORD}"
    schema: "dest_schema"
  
  migration_settings:
    auto_approve: false
    dry_run: false
  
  safety_settings:
    enable_safety_checks: true
    risk_tolerance: "medium"
```

### Environment Variables
Configuration files support environment variable substitution using `${VARIABLE_NAME}` syntax.

## 🛡️ Safety Features

### Safety Analysis
DDL Wizard analyzes operations for potential data loss:

- **Data Loss Detection**: Identifies operations that may cause data loss
- **Type Compatibility**: Checks column type changes for compatibility
- **Index Impact**: Analyzes index changes and performance implications
- **Risk Levels**: Categorizes risks as LOW, MEDIUM, HIGH, or CRITICAL

### Dependency Management
- **Foreign Key Analysis**: Identifies and respects foreign key relationships
- **Execution Ordering**: Orders operations to maintain referential integrity
- **Rollback Generation**: Creates reverse operations for safe rollbacks

## 📊 Visualization

Generate comprehensive schema documentation:

### Supported Formats
- **HTML Documentation**: Interactive table listings with relationships
- **Mermaid ER Diagrams**: Entity-relationship diagrams for modern documentation
- **Graphviz DOT**: Traditional ER diagrams for detailed visualization
- **JSON Export**: Machine-readable schema structure

### Example Output
```bash
python main.py --mode visualize --source-host localhost --source-user root --source-password password --source-schema mydb
```

Generates:
- `documentation/schema_documentation.html`
- `documentation/schema_erd.mmd`
- `documentation/schema_erd.dot`
- `documentation/schema_structure.json`

## 📈 Migration History

Track all migration executions with detailed logging:

### Features
- **Execution Tracking**: Record start time, duration, and status
- **Operation Details**: Track individual SQL statement execution
- **Rollback History**: Maintain rollback script references
- **Statistics**: Success rates, performance metrics
- **Export**: JSON/CSV export for reporting

### View History
```bash
python main.py --mode history
```

## 🎨 Interactive Mode

Enhanced user experience with:

- **Colored Output**: Status indicators and warnings with color coding
- **Progress Tracking**: Real-time progress bars for long operations
- **Confirmation Prompts**: Safety confirmations for risky operations
- **Summary Reports**: Clear operation summaries

## 📝 Command Line Options

### Database Connection
```bash
--source-host HOST          Source database host
--source-port PORT          Source database port (default: 3306)
--source-user USER          Source database username
--source-password PASSWORD  Source database password
--source-schema SCHEMA      Source schema name

--dest-host HOST            Destination database host
--dest-port PORT            Destination database port (default: 3306)
--dest-user USER            Destination database username
--dest-password PASSWORD    Destination database password
--dest-schema SCHEMA        Destination schema name
```

### Configuration
```bash
--config FILE               Configuration file path
--profile PROFILE           Configuration profile to use
```

### Operation Control
```bash
--mode MODE                 Operation mode (compare|extract|visualize|history)
--interactive              Enable interactive mode
--auto-approve             Auto-approve all operations
--dry-run                  Generate SQL without executing
--skip-safety-checks       Skip safety analysis
--visualize                Generate schema visualizations
```

### Output Options
```bash
--output-dir DIR           Output directory (default: ./ddl_output)
--migration-file FILE      Migration SQL filename (default: migration.sql)
--rollback-file FILE       Rollback SQL filename (default: rollback.sql)
--verbose                  Enable verbose logging
```

## 📂 Output Structure

DDL Wizard creates organized output directories:

```
ddl_output/
├── tables/
│   ├── table1.sql
│   ├── table2.sql
│   └── ...
├── functions/
│   ├── function1.sql
│   └── ...
├── procedures/
│   ├── procedure1.sql
│   └── ...
├── triggers/
│   ├── trigger1.sql
│   └── ...
├── events/
│   ├── event1.sql
│   └── ...
├── migration.sql
├── rollback.sql
├── comparison_report.txt
├── migration_report.md
└── documentation/
    ├── schema_documentation.html
    ├── schema_erd.mmd
    └── schema_structure.json
```

## 🔍 Troubleshooting

### Connection Issues
- Verify database credentials and network connectivity
- Check firewall settings for database ports
- Ensure user has necessary privileges (SELECT, SHOW permissions)

### Permission Requirements
- `SELECT` privilege on target schemas
- `SHOW VIEW` privilege for view definitions
- `PROCESS` privilege for function/procedure extraction

### Common Issues
- **Missing ALTER Generator**: Ensure all required modules are installed
- **Git Errors**: Verify Git is installed and repository is initialized
- **Memory Issues**: Use `--verbose` for detailed logging

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new features
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- Built for MariaDB and MySQL database systems
- Uses PyMySQL for pure Python database connectivity
- Git integration via GitPython
- YAML configuration with PyYAML
