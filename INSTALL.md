# DDL Wizard - Complete Installation Guide

This guide provides step-by-step installation instructions for DDL Wizard, including troubleshooting and testing procedures.

## 📋 System Requirements

### Minimum Requirements
- **Python**: 3.8 or higher (3.9+ recommended)
- **Operating System**: Linux, macOS, or Windows
- **Database**: MariaDB 10.3+ or MySQL 5.7+
- **Memory**: 512MB RAM minimum (1GB+ for large schemas)
- **Disk Space**: 100MB for installation + space for git repositories

### Database Privileges Required
The database user needs these minimum privileges:
- `SELECT` - Read schema information
- `SHOW DATABASES` - List available schemas
- `SHOW` - Show database objects

For full functionality (migration execution):
- `CREATE`, `DROP`, `ALTER` - Modify database objects
- `INSERT`, `UPDATE`, `DELETE` - Data operations (if needed)

## 🚀 Installation Methods

### Method 1: Standard Installation (Recommended)

1. **Install Python** (if not already installed):
   ```bash
   # Check current version
   python --version
   
   # If Python 3.8+ not available, install it:
   # Ubuntu/Debian:
   sudo apt update && sudo apt install python3.9 python3.9-pip python3.9-venv
   
   # macOS (with Homebrew):
   brew install python@3.9
   
   # Windows: Download from https://python.org
   ```

2. **Clone DDL Wizard**:
   ```bash
   git clone https://github.com/claudionanni/ddlwizard.git
   cd ddlwizard
   ```

3. **Create Virtual Environment** (recommended):
   ```bash
   python -m venv venv
   
   # Activate environment:
   # Linux/macOS:
   source venv/bin/activate
   
   # Windows:
   venv\Scripts\activate
   ```

4. **Install Dependencies**:
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

5. **Verify Installation**:
   ```bash
   python ddl_wizard.py --help
   ```

### Method 2: Docker-Based Testing

For quick testing without local database setup:

1. **Install Docker** (if not available):
   - Follow instructions at https://docs.docker.com/get-docker/

2. **Clone and Setup**:
   ```bash
   git clone https://github.com/claudionanni/ddlwizard.git
   cd ddlwizard
   pip install -r requirements.txt
   ```

3. **Start Test Databases**:
   ```bash
   cd testdata
   docker-compose up -d
   ```

4. **Test Connection**:
   ```bash
   python ../ddl_wizard.py compare \
     --source-host 127.0.0.1 --source-port 10622 --source-user sstuser --source-password sstpwd --source-schema ddlwizard_source_test \
     --dest-host 127.0.0.1 --dest-port 20622 --dest-user sstuser --dest-password sstpwd --dest-schema ddlwizard_dest_test \
     --dry-run
   ```

## 🧪 Testing Your Installation

### Quick Test (5 minutes)

1. **Test CLI Help**:
   ```bash
   python ddl_wizard.py --help
   # Should show available commands and options
   ```

2. **Test GUI** (optional):
   ```bash
   streamlit run ddlwizard/gui.py --server.port 8501
   # Should open web interface at http://localhost:8501
   ```

### Full Test with Sample Data (10 minutes)

1. **Create Test Databases**:
   ```bash
   # Connect to your MariaDB/MySQL
   mysql -u root -p
   ```
   
   ```sql
   CREATE DATABASE ddlwizard_source_test;
   CREATE DATABASE ddlwizard_dest_test;
   
   -- Create test user (optional)
   CREATE USER 'ddltest'@'localhost' IDENTIFIED BY 'testpass123';
   GRANT ALL PRIVILEGES ON ddlwizard_source_test.* TO 'ddltest'@'localhost';
   GRANT ALL PRIVILEGES ON ddlwizard_dest_test.* TO 'ddltest'@'localhost';
   FLUSH PRIVILEGES;
   EXIT;
   ```

2. **Load Sample Schemas**:
   ```bash
   # Load test data
   mysql -u ddltest -ptestpass123 ddlwizard_source_test < testdata/simpledata/source_schema.sql
   mysql -u ddltest -ptestpass123 ddlwizard_dest_test < testdata/simpledata/destination_schema.sql
   ```

3. **Run Comparison**:
   ```bash
   python ddl_wizard.py compare \
     --source-host localhost --source-user ddltest --source-password testpass123 --source-schema ddlwizard_source_test \
     --dest-host localhost --dest-user ddltest --dest-password testpass123 --dest-schema ddlwizard_dest_test
   ```

4. **Expected Result**:
   - Should generate `migration.sql` and `rollback.sql` files
   - Console should show differences found
   - Files should contain DDL statements

### Test Migration Execution (Advanced)

⚠️ **WARNING**: Only run on test databases!

```bash
# Generate migration
python ddl_wizard.py generate-migration \
  --source-host localhost --source-user ddltest --source-password testpass123 --source-schema ddlwizard_source_test \
  --dest-host localhost --dest-user ddltest --dest-password testpass123 --dest-schema ddlwizard_dest_test

# Execute migration
python ddl_wizard.py migrate \
  --dest-host localhost --dest-user ddltest --dest-password testpass123 --dest-schema ddlwizard_dest_test

# Test rollback
python ddl_wizard.py rollback \
  --dest-host localhost --dest-user ddltest --dest-password testpass123 --dest-schema ddlwizard_dest_test
```

## 🔧 Troubleshooting

### Python Issues

**Problem**: "Python not found" or wrong version
```bash
# Check available Python versions
python --version
python3 --version
python3.9 --version

# Use specific version if needed
python3.9 ddl_wizard.py --help
```

**Problem**: "pip not found"
```bash
# Install pip
python -m ensurepip --upgrade

# Or use system package manager:
# Ubuntu/Debian:
sudo apt install python3-pip

# macOS:
brew install python@3.9  # includes pip
```

### Dependency Issues

**Problem**: "ModuleNotFoundError"
```bash
# Upgrade pip first
pip install --upgrade pip

# Reinstall requirements
pip install -r requirements.txt --force-reinstall

# Check what's installed
pip list
```

**Problem**: Version conflicts
```bash
# Create fresh virtual environment
rm -rf venv
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
```

### Database Connection Issues

**Problem**: "Can't connect to database"
1. **Check database is running**:
   ```bash
   # Test connection manually
   mysql -h localhost -u root -p
   ```

2. **Verify connection parameters**:
   - Host: Usually `localhost` or `127.0.0.1`
   - Port: Usually `3306` for MySQL/MariaDB
   - Username/Password: Check credentials
   - Schema: Database must exist

3. **Check firewall**:
   ```bash
   # Test port connectivity
   telnet localhost 3306
   ```

**Problem**: "Access denied" errors
1. **Verify user privileges**:
   ```sql
   SHOW GRANTS FOR 'username'@'localhost';
   ```

2. **Grant minimum required privileges**:
   ```sql
   GRANT SELECT, SHOW DATABASES ON *.* TO 'username'@'localhost';
   FLUSH PRIVILEGES;
   ```

### Common File Issues

**Problem**: "Permission denied" on files
```bash
# Check permissions
ls -la ddl_wizard.py

# Fix if needed
chmod +x ddl_wizard.py
```

**Problem**: "File not found" errors
```bash
# Verify you're in the correct directory
pwd
ls ddl_wizard.py  # Should exist

# Check Python path
which python
```

## 🎯 Quick Start Commands

Once installed, these commands will get you started:

```bash
# Show help
python ddl_wizard.py --help

# Compare two schemas
python ddl_wizard.py compare \
  --source-host HOST1 --source-user USER1 --source-password PASS1 --source-schema SCHEMA1 \
  --dest-host HOST2 --dest-user USER2 --dest-password PASS2 --dest-schema SCHEMA2

# Start web interface
streamlit run ddlwizard/gui.py --server.port 8501

# Initialize git repository for schema versioning
python ddl_wizard.py init-git

# Generate migration without executing
python ddl_wizard.py generate-migration [connection options] --dry-run
```

## 📚 Next Steps

- **Read the main README.md** for feature overview and usage examples
- **Check testdata/README.md** for detailed testing scenarios
- **Explore the web GUI** at http://localhost:8501 after running Streamlit
- **Set up your own test databases** for safe experimentation

## 🆘 Getting Help

If you encounter issues not covered here:

1. **Check the logs**: DDL Wizard creates `ddl_wizard.log` with detailed information
2. **Review error messages**: They often contain specific guidance
3. **Test with sample data**: Use the provided test schemas to isolate issues
4. **Verify prerequisites**: Ensure Python 3.8+, database connectivity, and required privileges

The tool is designed to fail safely - it won't execute destructive operations without explicit confirmation.
