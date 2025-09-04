"""
DDL Wizard Streamlit GUI
========================

Web-based graphical user interface for DDL Wizard.
This provides an easy-to-use interface for database schema migrations.
"""

import streamlit as st
import os
import json
import traceback
from pathlib import Path
from typing import Dict, Any

from database import DatabaseConfig
from config_manager import DDLWizardConfig, DatabaseConnection, DatabaseSettings, OutputSettings, SafetySettings
from ddl_wizard_core import run_complete_migration
from connection_manager import ConnectionManager


# Set page configuration
st.set_page_config(
    page_title="DDL Wizard",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Display logo and title
logo_path = Path(__file__).parent / "img" / "ddlwizard-logo.png"
if logo_path.exists():
    col1, col2 = st.columns([1, 4])
    with col1:
        st.image(str(logo_path), width=120)
    with col2:
        st.markdown("## DDL Wizard")
        st.markdown("*Database Schema Migration Tool*")
else:
    st.title("DDL Wizard")

# Custom CSS
st.markdown("""
<style>
.main > div {
    padding-top: 2rem;
}
.stAlert {
    margin-bottom: 1rem;
}
.sql-container {
    background-color: #f0f2f6;
    border-radius: 0.5rem;
    padding: 1rem;
    margin: 1rem 0;
}
</style>
""", unsafe_allow_html=True)


def initialize_session_state():
    """Initialize session state variables."""
    if 'migration_results' not in st.session_state:
        st.session_state.migration_results = None
    if 'last_migration_successful' not in st.session_state:
        st.session_state.last_migration_successful = False
    if 'execution_results' not in st.session_state:
        st.session_state.execution_results = None
    if 'source_config' not in st.session_state:
        st.session_state.source_config = None
    if 'dest_config' not in st.session_state:
        st.session_state.dest_config = None
    if 'connection_manager' not in st.session_state:
        st.session_state.connection_manager = ConnectionManager()


def create_database_config_form(prefix: str, label: str) -> DatabaseConfig:
    """
    Create a form for database configuration with connection management.
    
    Args:
        prefix: Prefix for form keys
        label: Display label for the form
        
    Returns:
        DatabaseConfig: Database configuration object
    """
    with st.expander(f"🗄️ {label} Database Configuration", expanded=True):
        
        # Connection Management Section
        st.markdown("**💾 Saved Connections**")
        
        # Get saved connections
        saved_connections = st.session_state.connection_manager.list_connections()
        
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col1:
            if saved_connections:
                connection_names = [""] + list(saved_connections.keys())
                selected_connection = st.selectbox(
                    f"Load saved connection:",
                    connection_names,
                    key=f"{prefix}_saved_connection",
                    help="Select a previously saved connection"
                )
            else:
                selected_connection = ""
                st.info("No saved connections available")
        
        with col2:
            show_manage = st.button(f"📋 Manage", key=f"{prefix}_manage", help="Manage saved connections")
        
        with col3:
            show_save = st.button(f"💾 Save", key=f"{prefix}_save", help="Save current connection")
        
        # Load selected connection if any
        loaded_config = None
        if selected_connection and selected_connection in saved_connections:
            loaded_config = st.session_state.connection_manager.load_connection(selected_connection)
            if loaded_config:
                st.success(f"✅ Loaded connection: {selected_connection}")
                conn_info = saved_connections[selected_connection]
                if conn_info.get('description'):
                    st.info(f"📝 {conn_info['description']}")
        
        st.markdown("---")
        st.markdown("**🔧 Connection Parameters**")
        
        # Database configuration form
        col1, col2 = st.columns(2)
        
        with col1:
            host = st.text_input(
                f"Host", 
                value=loaded_config.host if loaded_config else "localhost", 
                key=f"{prefix}_host"
            )
            port = st.number_input(
                f"Port", 
                min_value=1, 
                max_value=65535, 
                value=loaded_config.port if loaded_config else 3306, 
                key=f"{prefix}_port"
            )
            username = st.text_input(
                f"Username", 
                value=loaded_config.user if loaded_config else "root", 
                key=f"{prefix}_username"
            )
        
        with col2:
            password = st.text_input(f"Password", type="password", key=f"{prefix}_password")
            schema = st.text_input(
                f"Schema/Database", 
                value=loaded_config.schema if loaded_config else "", 
                key=f"{prefix}_schema"
            )
            
        # Connection test button
        if st.button(f"Test {label} Connection", key=f"{prefix}_test"):
            if all([host, port, username, schema]):
                try:
                    config = DatabaseConfig(host, port, username, password or "", schema)
                    from database import DatabaseManager
                    db = DatabaseManager(config)
                    if db.test_connection():
                        st.success(f"✅ {label} connection successful!")
                    else:
                        st.error(f"❌ {label} connection failed!")
                except Exception as e:
                    st.error(f"❌ {label} connection error: {str(e)}")
            else:
                st.warning("Please fill in all required fields")
        
        # Handle Save Connection
        if show_save:
            st.session_state[f"{prefix}_show_save_dialog"] = True
        
        if st.session_state.get(f"{prefix}_show_save_dialog", False):
            with st.container():
                st.markdown("**💾 Save Connection**")
                
                col1, col2 = st.columns(2)
                with col1:
                    save_name = st.text_input(f"Connection Name:", key=f"{prefix}_save_name")
                with col2:
                    save_description = st.text_input(f"Description (optional):", key=f"{prefix}_save_description")
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    if st.button(f"💾 Save", key=f"{prefix}_save_confirm"):
                        if save_name and all([host, port, username, schema]):
                            config = DatabaseConfig(host, port, username, "", schema)  # Don't save password
                            success = st.session_state.connection_manager.save_connection(
                                save_name, config, save_description
                            )
                            if success:
                                st.success(f"✅ Connection '{save_name}' saved!")
                                st.session_state[f"{prefix}_show_save_dialog"] = False
                                st.rerun()
                            else:
                                st.error("❌ Failed to save connection")
                        else:
                            st.warning("Please provide a name and fill in all connection fields")
                
                with col2:
                    if st.button(f"❌ Cancel", key=f"{prefix}_save_cancel"):
                        st.session_state[f"{prefix}_show_save_dialog"] = False
                        st.rerun()
        
        # Handle Manage Connections
        if show_manage:
            st.session_state[f"{prefix}_show_manage_dialog"] = True
        
        if st.session_state.get(f"{prefix}_show_manage_dialog", False):
            create_connection_management_dialog(prefix)
    
    # Return config with defaults for empty fields to avoid validation errors
    return DatabaseConfig(
        host=host or "localhost", 
        port=port or 3306, 
        user=username or "root", 
        password=password or "", 
        schema=schema or "test"
    )


def create_connection_management_dialog(prefix: str):
    """Create a dialog for managing saved connections."""
    with st.container():
        st.markdown("**📋 Manage Saved Connections**")
        
        saved_connections = st.session_state.connection_manager.list_connections()
        
        if not saved_connections:
            st.info("No saved connections to manage")
        else:
            # Display connections in a table format
            for name, info in saved_connections.items():
                with st.container():
                    col1, col2, col3, col4 = st.columns([2, 2, 1, 1])
                    
                    with col1:
                        st.markdown(f"**{name}**")
                        st.text(f"{info['user']}@{info['host']}:{info['port']}/{info['schema']}")
                    
                    with col2:
                        st.text(info.get('description', 'No description'))
                        st.text(f"Last used: {info.get('last_used', 'Never')}")
                    
                    with col3:
                        if st.button(f"✏️ Edit", key=f"{prefix}_edit_{name}"):
                            st.session_state[f"{prefix}_edit_connection"] = name
                    
                    with col4:
                        if st.button(f"🗑️ Delete", key=f"{prefix}_delete_{name}"):
                            if st.session_state.connection_manager.delete_connection(name):
                                st.success(f"Deleted '{name}'")
                                st.rerun()
                            else:
                                st.error(f"Failed to delete '{name}'")
                    
                    st.markdown("---")
        
        # Export/Import buttons
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button(f"📤 Export All", key=f"{prefix}_export"):
                export_path = f"ddlwizard_connections_{prefix}.json"
                if st.session_state.connection_manager.export_connections(export_path):
                    st.success(f"Exported to {export_path}")
                    with open(export_path, 'r') as f:
                        st.download_button(
                            "⬇️ Download Export File",
                            f.read(),
                            file_name=export_path,
                            mime="application/json"
                        )
        
        with col2:
            uploaded_file = st.file_uploader(
                "📥 Import Connections",
                type=['json'],
                key=f"{prefix}_import"
            )
            if uploaded_file:
                import tempfile
                with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp_file:
                    tmp_file.write(uploaded_file.read().decode('utf-8'))
                    imported_count = st.session_state.connection_manager.import_connections(tmp_file.name)
                    if imported_count > 0:
                        st.success(f"Imported {imported_count} connections")
                        st.rerun()
                    else:
                        st.error("No connections imported")
                os.unlink(tmp_file.name)
        
        with col3:
            if st.button(f"❌ Close", key=f"{prefix}_manage_close"):
                st.session_state[f"{prefix}_show_manage_dialog"] = False
                st.rerun()


def create_migration_settings() -> tuple:
    """
    Create migration settings form.
    
    Returns:
        tuple: (output_dir, skip_safety_checks, enable_visualization)
    """
    with st.expander("⚙️ Migration Settings", expanded=True):
        col1, col2 = st.columns(2)
        
        with col1:
            output_dir = st.text_input(
                "Output Directory", 
                value="./ddl_output",
                help="Directory where migration files will be saved"
            )
            skip_safety_checks = st.checkbox(
                "Skip Safety Analysis",
                value=False,
                help="Skip safety warnings and validation checks"
            )
        
        with col2:
            enable_visualization = st.checkbox(
                "Generate Schema Visualization",
                value=True,
                help="Generate schema documentation and visualizations"
            )
            
            # Create output directory if it doesn't exist
            if st.button("Create Output Directory"):
                try:
                    Path(output_dir).mkdir(parents=True, exist_ok=True)
                    st.success(f"✅ Directory created: {output_dir}")
                except Exception as e:
                    st.error(f"❌ Failed to create directory: {str(e)}")
    
    return output_dir, skip_safety_checks, enable_visualization


def display_migration_results(results: Dict[str, Any]):
    """
    Display migration results in a nice format.
    
    Args:
        results: Migration results dictionary
    """
    st.success("🎉 Migration completed successfully!")
    
    # Summary metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Migration ID", results['migration_id'])
    
    with col2:
        st.metric("Operations", results['operation_count'])
    
    with col3:
        st.metric("Safety Warnings", len(results['safety_warnings']))
    
    with col4:
        if results['safety_warnings']:
            st.metric("Status", "⚠️ With Warnings", delta="Review Required")
        else:
            st.metric("Status", "✅ Clean", delta="No Issues")
    
    # File downloads
    st.subheader("📁 Generated Files")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if os.path.exists(results['migration_file']):
            with open(results['migration_file'], 'r') as f:
                migration_content = f.read()
            st.download_button(
                "⬇️ Download Migration SQL",
                migration_content,
                file_name=os.path.basename(results['migration_file']),
                mime="text/sql"
            )
    
    with col2:
        if os.path.exists(results['rollback_file']):
            with open(results['rollback_file'], 'r') as f:
                rollback_content = f.read()
            st.download_button(
                "⬇️ Download Rollback SQL",
                rollback_content,
                file_name=os.path.basename(results['rollback_file']),
                mime="text/sql"
            )
    
    with col3:
        if os.path.exists(results['migration_report_file']):
            with open(results['migration_report_file'], 'r') as f:
                report_content = f.read()
            st.download_button(
                "⬇️ Download Migration Report",
                report_content,
                file_name=os.path.basename(results['migration_report_file']),
                mime="text/markdown"
            )
    
    # Display SQL content
    if st.checkbox("Show Migration SQL", value=False):
        st.subheader("🔄 Migration SQL")
        st.code(results['migration_sql'], language='sql')
    
    if st.checkbox("Show Rollback SQL", value=False):
        st.subheader("↩️ Rollback SQL")
        st.code(results['rollback_sql'], language='sql')
    
    # Display safety warnings if any
    if results['safety_warnings']:
        st.subheader("⚠️ Safety Warnings")
        for warning in results['safety_warnings']:
            if warning['level'] == 'HIGH':
                st.error(f"🔴 **{warning['level']}:** {warning['message']}")
            elif warning['level'] == 'MEDIUM':
                st.warning(f"🟡 **{warning['level']}:** {warning['message']}")
            else:
                st.info(f"🔵 **{warning['level']}:** {warning['message']}")
    
    # Comparison details
    if st.checkbox("Show Detailed Comparison", value=False):
        st.subheader("🔍 Schema Comparison Details")
        st.json(results['comparison'])


def display_execution_results(execution_results: Dict[str, Any]):
    """
    Display SQL execution results.
    
    Args:
        execution_results: Execution results dictionary
    """
    if execution_results['success']:
        st.success("✅ SQL execution completed successfully!")
    else:
        st.error("❌ SQL execution failed!")
    
    # Summary metrics
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Executed Statements", execution_results['executed_statements'])
    
    with col2:
        st.metric("Failed Statements", execution_results['failed_statements'])
    
    with col3:
        st.metric("Execution Time", f"{execution_results['execution_time']:.2f}s")
    
    # Show errors if any
    if execution_results['errors']:
        st.subheader("❌ Errors")
        for error in execution_results['errors']:
            st.error(error)
    
    # Show warnings if any
    if execution_results['warnings']:
        st.subheader("⚠️ Warnings")
        for warning in execution_results['warnings']:
            st.warning(warning)


def create_sql_execution_section():
    """
    Create SQL execution section for applying migration/rollback files.
    """
    st.header("⚡ Execute Migration Files")
    st.markdown("**Execute migration or rollback SQL files against a database.**")
    
    # Database selection
    st.subheader("🗄️ Target Database")
    
    # Choice between existing connections or new one
    connection_choice = st.radio(
        "Choose connection:",
        ["Use Source Connection", "Use Destination Connection", "Use Saved Connection", "Configure New Connection"],
        horizontal=True
    )
    
    target_config = None
    
    if connection_choice == "Use Source Connection":
        if st.session_state.source_config:
            target_config = st.session_state.source_config
            st.info("Using source database connection")
        else:
            st.warning("Please configure source database connection first")
    elif connection_choice == "Use Destination Connection":
        if st.session_state.dest_config:
            target_config = st.session_state.dest_config
            st.info("Using destination database connection")
        else:
            st.warning("Please configure destination database connection first")
    elif connection_choice == "Use Saved Connection":
        # Load saved connection
        saved_connections = st.session_state.connection_manager.list_connections()
        
        if saved_connections:
            selected_saved = st.selectbox(
                "Select saved connection:",
                list(saved_connections.keys()),
                help="Choose from your saved connections"
            )
            
            if selected_saved:
                loaded_config = st.session_state.connection_manager.load_connection(selected_saved)
                if loaded_config:
                    # Need password for execution
                    execution_password = st.text_input(
                        f"Password for {selected_saved}:",
                        type="password",
                        help="Enter password for the saved connection"
                    )
                    
                    if execution_password:
                        target_config = DatabaseConfig(
                            host=loaded_config.host,
                            port=loaded_config.port,
                            user=loaded_config.user,
                            password=execution_password,
                            schema=loaded_config.schema
                        )
                        st.success(f"✅ Using saved connection: {selected_saved}")
                        
                        # Show connection details
                        conn_info = saved_connections[selected_saved]
                        st.info(f"📍 {conn_info['user']}@{conn_info['host']}:{conn_info['port']}/{conn_info['schema']}")
        else:
            st.warning("No saved connections available")
    else:
        # New connection configuration
        target_config = create_database_config_form("target", "Target")
    
    # File selection
    st.subheader("📄 SQL File Selection")
    
    # File source choice
    file_source = st.radio(
        "Choose SQL file source:",
        ["Upload File", "Select from Output Directory"],
        horizontal=True
    )
    
    sql_file_path = None
    sql_content = None
    
    if file_source == "Upload File":
        uploaded_file = st.file_uploader(
            "Choose SQL file",
            type=['sql'],
            help="Upload a migration or rollback SQL file"
        )
        
        if uploaded_file is not None:
            sql_content = uploaded_file.read().decode('utf-8')
            # Save temporarily
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', suffix='.sql', delete=False) as tmp_file:
                tmp_file.write(sql_content)
                sql_file_path = tmp_file.name
            
            st.success(f"✅ File uploaded: {uploaded_file.name}")
            
            # Preview content
            if st.checkbox("Preview SQL Content", value=False):
                st.code(sql_content, language='sql')
    
    else:
        # Select from output directory
        output_dir = st.text_input("Output Directory", value="./ddl_output")
        
        if os.path.exists(output_dir):
            sql_files = []
            for file in os.listdir(output_dir):
                if file.endswith('.sql'):
                    sql_files.append(os.path.join(output_dir, file))
            
            if sql_files:
                selected_file = st.selectbox(
                    "Select SQL file:",
                    sql_files,
                    format_func=lambda x: os.path.basename(x)
                )
                
                if selected_file:
                    sql_file_path = selected_file
                    
                    # Read and preview content
                    with open(selected_file, 'r') as f:
                        sql_content = f.read()
                    
                    st.success(f"✅ File selected: {os.path.basename(selected_file)}")
                    
                    if st.checkbox("Preview SQL Content", value=False):
                        st.code(sql_content, language='sql')
            else:
                st.warning("No SQL files found in the output directory")
        else:
            st.warning("Output directory does not exist")
    
    # Execution options
    st.subheader("⚙️ Execution Options")
    
    col1, col2 = st.columns(2)
    
    with col1:
        dry_run = st.checkbox(
            "Dry Run (Validate Only)",
            value=True,
            help="Validate SQL without actually executing it"
        )
    
    with col2:
        confirm_execution = st.checkbox(
            "I understand the risks",
            value=False,
            help="Confirm that you understand this will modify the database"
        )
    
    # Safety warnings
    if not dry_run:
        st.warning("⚠️ **CAUTION:** This will execute SQL statements against the selected database!")
        st.markdown("""
        - Make sure you have a backup of your database
        - Review the SQL content carefully before execution
        - Test on a non-production environment first
        - Ensure you have appropriate database permissions
        """)
    
    # Execute button
    can_execute = (target_config is not None and 
                   sql_file_path is not None and 
                   (dry_run or confirm_execution))
    
    if st.button(
        "🚀 Execute SQL" if not dry_run else "🔍 Validate SQL",
        type="primary",
        disabled=not can_execute,
        help="Execute or validate the selected SQL file"
    ):
        if not can_execute:
            st.error("Please complete all required fields and confirmations")
            return
        
        # Execute SQL
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        try:
            status_text.text("🔗 Connecting to target database...")
            progress_bar.progress(20)
            
            from database import DatabaseManager
            db = DatabaseManager(target_config)
            
            if not db.test_connection():
                st.error("❌ Failed to connect to target database")
                return
            
            status_text.text("🔍 Validating SQL content..." if dry_run else "⚡ Executing SQL statements...")
            progress_bar.progress(50)
            
            # Execute the SQL file
            execution_results = db.execute_sql_file(sql_file_path, dry_run=dry_run)
            
            progress_bar.progress(100)
            status_text.text("✅ Execution completed!")
            
            # Store results in session state
            st.session_state.execution_results = execution_results
            
            # Display results
            display_execution_results(execution_results)
            
        except Exception as e:
            st.error(f"❌ Execution failed: {str(e)}")
            st.error("**Error Details:**")
            st.code(traceback.format_exc())
            
        finally:
            progress_bar.empty()
            status_text.empty()
            
            # Clean up temporary file if created
            if file_source == "Upload File" and sql_file_path:
                try:
                    os.unlink(sql_file_path)
                except:
                    pass


def display_sidebar_info():
    """Display information in the sidebar."""
    with st.sidebar:
        st.title("DDL Wizard")
        st.markdown("**Database Schema Migration Tool**")
        
        st.markdown("---")
        st.markdown("### 📋 What this tool does:")
        st.markdown("""
        - Compares database schemas
        - Generates migration SQL
        - Creates rollback scripts
        - Performs safety analysis
        - Tracks migration history
        - Generates documentation
        - **Executes migration files**
        - **Manages saved connections**
        """)
        
        st.markdown("---")
        st.markdown("### 🚀 How to use:")
        st.markdown("""
        1. Configure source database
        2. Configure destination database
        3. **Save connections for reuse**
        4. Set migration options
        5. Run migration analysis
        6. Download generated files
        7. **Execute migration/rollback**
        """)
        
        st.markdown("---")
        st.markdown("### 💾 Connection Features:")
        st.markdown("""
        - Save named connections
        - Load saved connections
        - Export/import connections
        - Connection descriptions
        - Usage tracking
        """)
        
        st.markdown("---")
        st.markdown("### ⚡ Execution Features:")
        st.markdown("""
        - Dry run validation
        - Connection reuse
        - File upload support
        - Error handling
        - Progress tracking
        """)
        
        st.markdown("---")
        st.markdown("### 💡 Tips:")
        st.markdown("""
        - **Save frequently used connections**
        - Test connections before running
        - Enable safety analysis for production
        - Review warnings carefully
        - Keep backups before applying
        - **Use dry run first**
        - **Test on non-production first**
        """)


def main():
    """Main Streamlit application."""
    initialize_session_state()
    display_sidebar_info()
    
    # Database configurations
    st.header("🗄️ Database Configuration")
    
    col1, col2 = st.columns(2)
    
    with col1:
        source_config = create_database_config_form("source", "Source")
        # Store in session state for reuse in execution
        st.session_state.source_config = source_config
    
    with col2:
        dest_config = create_database_config_form("dest", "Destination")
        # Store in session state for reuse in execution
        st.session_state.dest_config = dest_config
    
    # Migration settings
    st.header("⚙️ Migration Settings")
    output_dir, skip_safety_checks, enable_visualization = create_migration_settings()
    
    # Migration execution
    st.header("🚀 Run Migration Analysis")
    
    if st.button("🔄 Generate Migration", type="primary", help="Analyze schemas and generate migration files"):
        # Validate inputs
        required_fields = [
            (source_config.host, "Source Host"),
            (source_config.schema, "Source Schema"),
            (source_config.user, "Source Username"),
            (dest_config.host, "Destination Host"),
            (dest_config.schema, "Destination Schema"),
            (dest_config.user, "Destination Username"),
            (output_dir, "Output Directory")
        ]
        
        missing_fields = [field_name for field_value, field_name in required_fields if not field_value]
        
        if missing_fields:
            st.error(f"❌ Missing required fields: {', '.join(missing_fields)}")
            return
        
        # Run migration with progress
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        try:
            status_text.text("🔗 Connecting to databases...")
            progress_bar.progress(10)
            
            # Create DDL Wizard configuration
            config = DDLWizardConfig(
                source=DatabaseConnection(
                    host=source_config.host,
                    port=source_config.port,
                    user=source_config.user,
                    password=source_config.password,
                    schema=source_config.schema
                ),
                destination=DatabaseConnection(
                    host=dest_config.host,
                    port=dest_config.port,
                    user=dest_config.user,
                    password=dest_config.password,
                    schema=dest_config.schema
                ),
                safety=SafetySettings(),
                output=OutputSettings(output_dir=output_dir)
            )
            
            status_text.text("📊 Extracting schema objects...")
            progress_bar.progress(30)
            
            status_text.text("🔍 Comparing schemas...")
            progress_bar.progress(50)
            
            status_text.text("🛡️ Performing safety analysis...")
            progress_bar.progress(70)
            
            status_text.text("📝 Generating migration files...")
            progress_bar.progress(90)
            
            # Run the complete migration
            results = run_complete_migration(
                source_config=source_config,
                dest_config=dest_config,
                config=config,
                output_dir=output_dir,
                skip_safety_checks=skip_safety_checks,
                enable_visualization=enable_visualization
            )
            
            progress_bar.progress(100)
            status_text.text("✅ Migration analysis completed!")
            
            # Store results in session state
            st.session_state.migration_results = results
            st.session_state.last_migration_successful = True
            
            # Display results
            st.success("Migration analysis completed successfully!")
            
        except Exception as e:
            st.error(f"❌ Migration failed: {str(e)}")
            st.error("**Error Details:**")
            st.code(traceback.format_exc())
            
            st.session_state.last_migration_successful = False
            
        finally:
            progress_bar.empty()
            status_text.empty()
    
    # Display results if available
    if st.session_state.migration_results and st.session_state.last_migration_successful:
        st.header("📊 Migration Results")
        display_migration_results(st.session_state.migration_results)
    
    # SQL Execution Section
    st.markdown("---")
    create_sql_execution_section()
    
    # Footer
    st.markdown("---")
    st.markdown("""
    <div style='text-align: center; color: #666;'>
        <p>DDL Wizard v2.0 - Database Schema Migration Tool</p>
        <p>Built with ❤️ using Streamlit</p>
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
