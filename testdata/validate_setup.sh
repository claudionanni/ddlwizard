#!/bin/bash
# DDL Wizard Test Data Validator
# This script helps validate that the test schemas are set up correctly

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
DB_HOST="localhost"
DB_PORT="3306"
DB_USER="root"
DB_PASS=""
SOURCE_SCHEMA="ddlwizard_source_test"
DEST_SCHEMA="ddlwizard_dest_test"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --host)
            DB_HOST="$2"
            shift 2
            ;;
        --port)
            DB_PORT="$2"
            shift 2
            ;;
        --user)
            DB_USER="$2"
            shift 2
            ;;
        --password)
            DB_PASS="$2"
            shift 2
            ;;
        --source-schema)
            SOURCE_SCHEMA="$2"
            shift 2
            ;;
        --dest-schema)
            DEST_SCHEMA="$2"
            shift 2
            ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS]"
            echo "Options:"
            echo "  --host HOST           Database host (default: localhost)"
            echo "  --port PORT           Database port (default: 3306)"
            echo "  --user USER           Database user (default: root)"
            echo "  --password PASS       Database password (default: empty)"
            echo "  --source-schema NAME  Source schema name (default: ddlwizard_source_test)"
            echo "  --dest-schema NAME    Dest schema name (default: ddlwizard_dest_test)"
            echo "  -h, --help           Show this help"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Build MySQL command
MYSQL_CMD="mysql -h${DB_HOST} -P${DB_PORT} -u${DB_USER}"
if [ ! -z "$DB_PASS" ]; then
    MYSQL_CMD="${MYSQL_CMD} -p${DB_PASS}"
fi

echo -e "${BLUE}🧙‍♂️ DDL Wizard Test Data Validator${NC}"
echo "========================================"

# Test database connection
echo -n "Testing database connection... "
if $MYSQL_CMD -e "SELECT 1;" > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Connected${NC}"
else
    echo -e "${RED}✗ Connection failed${NC}"
    echo "Please check your database credentials and ensure the server is running."
    exit 1
fi

# Check source schema
echo -n "Checking source schema ($SOURCE_SCHEMA)... "
SOURCE_EXISTS=$($MYSQL_CMD -e "SELECT SCHEMA_NAME FROM INFORMATION_SCHEMA.SCHEMATA WHERE SCHEMA_NAME='$SOURCE_SCHEMA';" --silent --skip-column-names | wc -l)
if [ "$SOURCE_EXISTS" -eq 1 ]; then
    echo -e "${GREEN}✓ Found${NC}"
    
    # Count objects in source schema
    SOURCE_TABLES=$($MYSQL_CMD -e "SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA='$SOURCE_SCHEMA' AND TABLE_TYPE='BASE TABLE';" --silent --skip-column-names)
    SOURCE_VIEWS=$($MYSQL_CMD -e "SELECT COUNT(*) FROM INFORMATION_SCHEMA.VIEWS WHERE TABLE_SCHEMA='$SOURCE_SCHEMA';" --silent --skip-column-names)
    SOURCE_PROCEDURES=$($MYSQL_CMD -e "SELECT COUNT(*) FROM INFORMATION_SCHEMA.ROUTINES WHERE ROUTINE_SCHEMA='$SOURCE_SCHEMA' AND ROUTINE_TYPE='PROCEDURE';" --silent --skip-column-names)
    SOURCE_FUNCTIONS=$($MYSQL_CMD -e "SELECT COUNT(*) FROM INFORMATION_SCHEMA.ROUTINES WHERE ROUTINE_SCHEMA='$SOURCE_SCHEMA' AND ROUTINE_TYPE='FUNCTION';" --silent --skip-column-names)
    
    echo "  - Tables: $SOURCE_TABLES"
    echo "  - Views: $SOURCE_VIEWS" 
    echo "  - Procedures: $SOURCE_PROCEDURES"
    echo "  - Functions: $SOURCE_FUNCTIONS"
else
    echo -e "${RED}✗ Not found${NC}"
    echo -e "${YELLOW}  Run: mysql -u $DB_USER < testdata/source_schema.sql${NC}"
fi

# Check destination schema
echo -n "Checking destination schema ($DEST_SCHEMA)... "
DEST_EXISTS=$($MYSQL_CMD -e "SELECT SCHEMA_NAME FROM INFORMATION_SCHEMA.SCHEMATA WHERE SCHEMA_NAME='$DEST_SCHEMA';" --silent --skip-column-names | wc -l)
if [ "$DEST_EXISTS" -eq 1 ]; then
    echo -e "${GREEN}✓ Found${NC}"
    
    # Count objects in destination schema
    DEST_TABLES=$($MYSQL_CMD -e "SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA='$DEST_SCHEMA' AND TABLE_TYPE='BASE TABLE';" --silent --skip-column-names)
    DEST_VIEWS=$($MYSQL_CMD -e "SELECT COUNT(*) FROM INFORMATION_SCHEMA.VIEWS WHERE TABLE_SCHEMA='$DEST_SCHEMA';" --silent --skip-column-names)
    DEST_PROCEDURES=$($MYSQL_CMD -e "SELECT COUNT(*) FROM INFORMATION_SCHEMA.ROUTINES WHERE ROUTINE_SCHEMA='$DEST_SCHEMA' AND ROUTINE_TYPE='PROCEDURE';" --silent --skip-column-names)
    DEST_FUNCTIONS=$($MYSQL_CMD -e "SELECT COUNT(*) FROM INFORMATION_SCHEMA.ROUTINES WHERE ROUTINE_SCHEMA='$DEST_SCHEMA' AND ROUTINE_TYPE='FUNCTION';" --silent --skip-column-names)
    
    echo "  - Tables: $DEST_TABLES"
    echo "  - Views: $DEST_VIEWS"
    echo "  - Procedures: $DEST_PROCEDURES" 
    echo "  - Functions: $DEST_FUNCTIONS"
else
    echo -e "${RED}✗ Not found${NC}"
    echo -e "${YELLOW}  Run: mysql -u $DB_USER < testdata/destination_schema.sql${NC}"
fi

# Summary and next steps
echo ""
echo "========================================"
if [ "$SOURCE_EXISTS" -eq 1 ] && [ "$DEST_EXISTS" -eq 1 ]; then
    echo -e "${GREEN}🎉 Both test schemas are ready!${NC}"
    echo ""
    echo "Next steps:"
    echo "1. Test with CLI:"
    echo -e "   ${BLUE}python main.py compare \\${NC}"
    echo -e "   ${BLUE}     --source-host $DB_HOST --source-user $DB_USER --source-schema $SOURCE_SCHEMA \\${NC}"
    echo -e "   ${BLUE}     --dest-host $DB_HOST --dest-user $DB_USER --dest-schema $DEST_SCHEMA \\${NC}"
    echo -e "   ${BLUE}     --output-dir ./test_results${NC}"
    echo ""
    echo "2. Test with GUI:"
    echo -e "   ${BLUE}streamlit run ddlwizard/gui.py --server.port 8501${NC}"
else
    echo -e "${YELLOW}⚠️  Test schemas need to be set up${NC}"
    echo ""
    echo "Setup commands:"
    if [ "$SOURCE_EXISTS" -eq 0 ]; then
        echo -e "   ${BLUE}mysql -h $DB_HOST -P $DB_PORT -u $DB_USER < testdata/source_schema.sql${NC}"
    fi
    if [ "$DEST_EXISTS" -eq 0 ]; then
        echo -e "   ${BLUE}mysql -h $DB_HOST -P $DB_PORT -u $DB_USER < testdata/destination_schema.sql${NC}"
    fi
fi

echo ""
echo -e "${BLUE}📖 See testdata/README.md for detailed instructions${NC}"
