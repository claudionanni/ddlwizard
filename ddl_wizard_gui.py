"""
DDL Wizard Streamlit GUI
========================

Web-based graphical user interface for DDL Wizard.
This provides an easy-to-use interface for database schema migrations.
"""

import streamlit as st
import pandas as pd
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

# Custom CSS with improved styling
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

/* Scrollable SQL content containers */
.sql-content-container {
    max-height: 400px;
    overflow-y: auto;
    border: 1px solid #e0e0e0;
    border-radius: 8px;
    background-color: #f8f9fa;
    padding: 0;
    margin: 0.5rem 0;
}

.sql-content-container .stCodeBlock {
    max-height: 400px !important;
    overflow-y: auto !important;
}

.sql-content-container pre {
    max-height: 400px !important;
    overflow-y: auto !important;
    margin: 0 !important;
    padding: 1rem !important;
}

.sql-content-container::-webkit-scrollbar {
    width: 8px;
}

.sql-content-container::-webkit-scrollbar-track {
    background: #f1f1f1;
    border-radius: 4px;
}

.sql-content-container::-webkit-scrollbar-thumb {
    background: #c1c1c1;
    border-radius: 4px;
}

.sql-content-container::-webkit-scrollbar-thumb:hover {
    background: #a8a8a8;
}

/* Tab styling improvements */
.stTabs [data-baseweb="tab-list"] {
    gap: 8px;
}

.stTabs [data-baseweb="tab"] {
    height: 50px;
    padding-left: 20px;
    padding-right: 20px;
    background-color: #f0f2f6;
    border-radius: 10px 10px 0px 0px;
    color: #262730;
    font-weight: 600;
}

.stTabs [aria-selected="true"] {
    background-color: #ffffff;
    border-bottom: 3px solid #ff6b6b;
}

/* Section containers */
.section-container {
    background-color: #fafafa;
    padding: 1.5rem;
    border-radius: 10px;
    margin-bottom: 1rem;
    border-left: 4px solid #ff6b6b;
}

/* Success/error styling improvements */
.stSuccess {
    border-radius: 8px;
    padding: 1rem;
}

.stError {
    border-radius: 8px;
    padding: 1rem;
}

.stWarning {
    border-radius: 8px;
    padding: 1rem;
}

/* Button improvements */
.stButton > button {
    border-radius: 8px;
    font-weight: 500;
    transition: all 0.3s;
}

.stButton > button:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 8px rgba(0,0,0,0.1);
}

/* Metric styling */
.metric-container {
    background-color: #f8f9fa;
    padding: 1rem;
    border-radius: 8px;
    text-align: center;
    border: 1px solid #e9ecef;
}

/* Progress bar styling */
.stProgress .st-bo {
    background-color: #ff6b6b;
}

/* Expander styling */
.streamlit-expanderHeader {
    background-color: #f8f9fa;
    border-radius: 8px;
    font-weight: 600;
}

/* Connection status indicators */
.connection-status {
    display: inline-block;
    width: 12px;
    height: 12px;
    border-radius: 50%;
    margin-right: 8px;
}

.status-connected {
    background-color: #28a745;
}

.status-disconnected {
    background-color: #dc3545;
}

.status-unknown {
    background-color: #ffc107;
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
    if 'current_timestamp' not in st.session_state:
        from datetime import datetime
        st.session_state.current_timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    # Initialize these as well to avoid issues
    if 'output_dir' not in st.session_state:
        st.session_state.output_dir = './ddl_output'
    if 'skip_safety_checks' not in st.session_state:
        st.session_state.skip_safety_checks = False
    if 'enable_visualization' not in st.session_state:
        st.session_state.enable_visualization = True


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
    
    # Display SQL content in scrollable containers
    if st.checkbox("Show Migration SQL", value=False):
        st.subheader("🔄 Migration SQL")
        st.markdown("""
        <div class="sql-content-container" style="max-height: 400px;">
        """, unsafe_allow_html=True)
        st.code(results['migration_sql'], language='sql')
        st.markdown("</div>", unsafe_allow_html=True)
        
        # Show line count
        line_count = len(results['migration_sql'].split('\n'))
        st.caption(f"📏 {line_count} lines of SQL")
    
    if st.checkbox("Show Rollback SQL", value=False):
        st.subheader("↩️ Rollback SQL")
        st.markdown("""
        <div class="sql-content-container" style="max-height: 400px;">
        """, unsafe_allow_html=True)
        st.code(results['rollback_sql'], language='sql')
        st.markdown("</div>", unsafe_allow_html=True)
        
        # Show line count
        line_count = len(results['rollback_sql'].split('\n'))
        st.caption(f"📏 {line_count} lines of SQL")
    
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
    
    # Schema comparison summary table
    st.subheader("📊 Schema Comparison Summary")
    display_comparison_summary_table(results['comparison'])
    
    # Comparison details in scrollable container
    if st.checkbox("Show Detailed Comparison", value=False):
        st.subheader("🔍 Schema Comparison Details")
        st.markdown("""
        <div class="sql-content-container" style="max-height: 400px;">
        """, unsafe_allow_html=True)
        st.json(results['comparison'])
        st.markdown("</div>", unsafe_allow_html=True)


def display_comparison_summary_table(comparison_data: Dict[str, Any]):
    """
    Display a human-readable summary table of schema comparison results.
    
    Args:
        comparison_data: Comparison results from schema comparator
    """
    # Define object types with friendly names
    object_types = {
        'tables': '📊 Tables',
        'views': '👁️ Views', 
        'procedures': '⚙️ Procedures',
        'functions': '🔧 Functions',
        'triggers': '⚡ Triggers',
        'events': '⏰ Events',
        'sequences': '🔢 Sequences'
    }
    
    # Prepare data for the summary table
    summary_data = []
    
    for obj_type, friendly_name in object_types.items():
        if obj_type in comparison_data:
            obj_data = comparison_data[obj_type]
            
            # Calculate counts
            only_source = len(obj_data.get('only_in_source', []))
            only_dest = len(obj_data.get('only_in_dest', []))
            in_both = len(obj_data.get('in_both', []))
            
            # Determine migration actions
            will_be_created = only_source  # Objects only in source will be created in dest
            will_be_dropped = only_dest    # Objects only in dest will be dropped
            
            summary_data.append({
                'Object Type': friendly_name,
                'Only in Source': only_source,
                'Only in Destination': only_dest,
                'In Both': in_both,
                'Will be Created': f"✅ {will_be_created}" if will_be_created > 0 else "➖ 0",
                'Will be Dropped': f"🗑️ {will_be_dropped}" if will_be_dropped > 0 else "➖ 0",
                'Total Source': only_source + in_both,
                'Total Destination': only_dest + in_both
            })
    
    if summary_data:
        # Create DataFrame
        df = pd.DataFrame(summary_data)
        
        # Display the table
        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Object Type": st.column_config.TextColumn("Object Type", width="medium"),
                "Only in Source": st.column_config.NumberColumn("Only in Source", help="Objects that exist only in source schema"),
                "Only in Destination": st.column_config.NumberColumn("Only in Destination", help="Objects that exist only in destination schema"),
                "In Both": st.column_config.NumberColumn("In Both", help="Objects that exist in both schemas"),
                "Will be Created": st.column_config.TextColumn("Will be Created", help="Objects that will be created in destination"),
                "Will be Dropped": st.column_config.TextColumn("Will be Dropped", help="Objects that will be dropped from destination"),
                "Total Source": st.column_config.NumberColumn("Total Source", help="Total objects in source schema"),
                "Total Destination": st.column_config.NumberColumn("Total Destination", help="Total objects in destination schema")
            }
        )
        
        # Display summary statistics
        total_operations = sum(len(obj_data.get('only_in_source', [])) + len(obj_data.get('only_in_dest', [])) 
                             for obj_data in comparison_data.values())
        
        if total_operations > 0:
            st.info(f"📈 **Migration Summary**: {total_operations} total operations required to sync destination with source")
        else:
            st.success("✅ **Schemas are in sync**: No migration operations required")
            
        # Show object-specific details if requested
        if st.checkbox("Show Object Names", value=False):
            st.subheader("📝 Detailed Object Lists")
            
            for obj_type, friendly_name in object_types.items():
                if obj_type in comparison_data:
                    obj_data = comparison_data[obj_type]
                    
                    if (obj_data.get('only_in_source') or obj_data.get('only_in_dest')):
                        with st.expander(f"{friendly_name} Details"):
                            
                            col1, col2 = st.columns(2)
                            
                            with col1:
                                if obj_data.get('only_in_source'):
                                    st.markdown("**✅ Will be Created:**")
                                    for name in sorted(obj_data['only_in_source']):
                                        st.text(f"  • {name}")
                                else:
                                    st.text("No objects to create")
                            
                            with col2:
                                if obj_data.get('only_in_dest'):
                                    st.markdown("**🗑️ Will be Dropped:**")
                                    for name in sorted(obj_data['only_in_dest']):
                                        st.text(f"  • {name}")
                                else:
                                    st.text("No objects to drop")
    else:
        st.warning("⚠️ No comparison data available")


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
    
    # Database selection
    st.subheader("🗄️ Target Database")
    
    # Safety warning
    st.warning("⚠️ **IMPORTANT:** Double-check your target database selection! Migration/rollback files will be executed against the selected database.")
    
    # Choice between existing connections or new one (removed risky source option)
    connection_choice = st.radio(
        "Choose connection:",
        ["Use Destination Connection", "Use Saved Connection", "Configure New Connection"],
        horizontal=True,
        index=0,  # Default to "Use Destination Connection"
        help="Select the target database where migration/rollback SQL will be executed"
    )
    
    target_config = None
    
    if connection_choice == "Use Destination Connection":
        if st.session_state.dest_config:
            target_config = st.session_state.dest_config
            st.success("✅ Using destination database connection (recommended for migrations)")
            
            # Show connection details for verification
            if hasattr(st.session_state.dest_config, 'schema'):
                st.info(f"🎯 **Target:** {st.session_state.dest_config.user}@{st.session_state.dest_config.host}:{st.session_state.dest_config.port}/{st.session_state.dest_config.schema}")
        else:
            st.error("❌ Please configure destination database connection in the **Setup** tab first")
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
            
            # Preview content in scrollable container
            if st.checkbox("Preview SQL Content", value=False):
                st.markdown("**📄 SQL File Preview**")
                st.markdown("""
                <div class="sql-content-container" style="max-height: 400px;">
                """, unsafe_allow_html=True)
                st.code(sql_content, language='sql')
                st.markdown("</div>", unsafe_allow_html=True)
                
                # Show file stats
                line_count = len(sql_content.split('\n'))
                char_count = len(sql_content)
                st.caption(f"📏 {line_count} lines, {char_count:,} characters")
    
    else:
        # Select from output directory - use the value from Setup tab
        configured_output_dir = getattr(st.session_state, 'output_dir', './ddl_output')
        
        # Show sync status
        if configured_output_dir != './ddl_output':
            st.info(f"🔗 **Auto-synced from Setup tab:** `{configured_output_dir}`")
        
        output_dir = st.text_input(
            "Output Directory", 
            value=configured_output_dir,
            help=f"This directory is automatically synchronized with the Setup tab. Current value: {configured_output_dir}"
        )
        
        # Add sync button if user changed the value
        if output_dir != configured_output_dir:
            col1, col2 = st.columns(2)
            with col1:
                if st.button("🔄 Sync with Setup Tab", help="Reset to the output directory configured in Setup tab"):
                    output_dir = configured_output_dir
                    st.rerun()
            with col2:
                st.warning("⚠️ Directory differs from Setup tab configuration")
        
        if os.path.exists(output_dir):
            sql_files = []
            for file in os.listdir(output_dir):
                if file.endswith('.sql'):
                    sql_files.append(os.path.join(output_dir, file))
            
            if sql_files:
                st.success(f"✅ Found {len(sql_files)} SQL file(s) in `{output_dir}`")
                
                # Sort files to prefer migration.sql as default
                migration_files = [f for f in sql_files if 'migration.sql' in os.path.basename(f)]
                rollback_files = [f for f in sql_files if 'rollback.sql' in os.path.basename(f)]
                other_files = [f for f in sql_files if f not in migration_files and f not in rollback_files]
                
                # Reorder: migration files first, then rollback, then others
                sorted_files = migration_files + rollback_files + other_files
                
                # Find default index (prefer migration.sql)
                default_index = 0
                for i, file in enumerate(sorted_files):
                    if 'migration.sql' in os.path.basename(file):
                        default_index = i
                        break
                
                selected_file = st.selectbox(
                    "Select SQL file:",
                    sorted_files,
                    index=default_index,
                    format_func=lambda x: f"{'🔄 ' if 'migration' in os.path.basename(x) else '↩️ ' if 'rollback' in os.path.basename(x) else '📄 '}{os.path.basename(x)} ({os.path.getsize(x):,} bytes)",
                    help="🔄 Migration files apply changes forward, ↩️ Rollback files revert changes, 📄 Other SQL files"
                )
                
                if selected_file:
                    sql_file_path = selected_file
                    
                    # Show file type indicator
                    filename = os.path.basename(selected_file)
                    if 'migration' in filename:
                        st.success(f"🔄 **Migration File Selected:** {filename} - Applies changes to move database forward")
                    elif 'rollback' in filename:
                        st.warning(f"↩️ **Rollback File Selected:** {filename} - Reverts changes to previous state")
                    else:
                        st.info(f"📄 **SQL File Selected:** {filename} - Custom SQL file")
                    
                    # Read and preview content
                    with open(selected_file, 'r') as f:
                        sql_content = f.read()
                    
                    st.success(f"✅ File selected: {os.path.basename(selected_file)}")
                    
                    if st.checkbox("Preview SQL Content", value=False):
                        st.markdown("**📄 SQL File Preview**")
                        st.markdown("""
                        <div class="sql-content-container" style="max-height: 400px;">
                        """, unsafe_allow_html=True)
                        st.code(sql_content, language='sql')
                        st.markdown("</div>", unsafe_allow_html=True)
                        
                        # Show file stats
                        line_count = len(sql_content.split('\n'))
                        char_count = len(sql_content)
                        st.caption(f"📏 {line_count} lines, {char_count:,} characters")
            else:
                st.warning(f"📁 No SQL files found in `{output_dir}`")
                st.info("💡 Generate a migration in the **Migration** tab first, or upload a file above.")
        else:
            st.error(f"📁 Output directory `{output_dir}` does not exist")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("📁 Create Directory", help="Create the output directory"):
                    try:
                        os.makedirs(output_dir, exist_ok=True)
                        st.success(f"✅ Created directory: `{output_dir}`")
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Failed to create directory: {str(e)}")
            
            with col2:
                st.info("💡 Or go to **Setup** tab to configure a different output directory.")
    
    # Execution options
    st.subheader("⚙️ Execution Options")
    
    col1, col2 = st.columns(2)
    
    with col1:
        dry_run = st.checkbox(
            "Dry Run (Validate Only)",
            value=True,
            help="Validate SQL without actually executing it (RECOMMENDED for first run)"
        )
    
    with col2:
        confirm_execution = st.checkbox(
            "I understand the risks",
            value=False,
            help="Confirm that you understand this will modify the target database"
        )
    
    # Enhanced safety warnings
    if not dry_run:
        st.error("🚨 **DANGER ZONE:** This will execute SQL statements against the target database!")
        st.markdown("""
        **⚠️ CRITICAL SAFETY CHECKLIST:**
        - ✅ **Backup verified:** You have a recent backup of the target database
        - ✅ **Target confirmed:** You've double-checked the target database connection above
        - ✅ **SQL reviewed:** You've previewed the SQL content and understand what it will do
        - ✅ **Environment verified:** This is the correct environment (not accidentally production)
        - ✅ **Permissions confirmed:** You have the necessary database privileges
        - ✅ **Rollback ready:** You know how to rollback if something goes wrong
        """)
    else:
        st.info("🔍 **Dry Run Mode:** SQL will be validated but not executed. This is the safe way to test first.")
    
    # Final confirmation section (before button for better UX)
    final_confirm = True  # Default for dry run
    if not dry_run:
        st.warning("🛑 **FINAL CONFIRMATION REQUIRED**")
        
        # Show target database again for final verification
        if target_config:
            st.code(f"""
TARGET DATABASE DETAILS:
Host: {target_config.host}
Port: {target_config.port}
User: {target_config.user}
Schema: {target_config.schema}
            """)
        
        final_confirm = st.checkbox(
            "🚨 I CONFIRM: Execute SQL against the above database",
            value=False,
            help="Final confirmation before executing SQL"
        )
    
    # Execute button
    can_execute = (target_config is not None and 
                   sql_file_path is not None and 
                   (dry_run or confirm_execution) and
                   final_confirm)
    
    # Final execution button with enhanced safety
    button_color = "secondary" if dry_run else "primary"
    button_text = "🔍 Validate SQL (Safe)" if dry_run else "� Execute SQL (DANGER)"
    
    if st.button(
        button_text,
        type=button_color,
        disabled=not can_execute,
        help="Validate SQL safely" if dry_run else "⚠️ EXECUTE SQL AGAINST TARGET DATABASE ⚠️"
    ):
        if not can_execute:
            st.error("❌ Please complete all required fields and confirmations")
            return
        
        # Execute immediately for dry run, already confirmed for dangerous execution
        
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


def test_database_connection(config: DatabaseConfig, label: str) -> bool:
    """
    Test database connection and display result.
    
    Args:
        config: Database configuration
        label: Display label for the connection
        
    Returns:
        bool: True if connection successful, False otherwise
    """
    try:
        from database import DatabaseManager
        db = DatabaseManager(config)
        if db.test_connection():
            st.success(f"✅ {label} connection successful!")
            return True
        else:
            st.error(f"❌ {label} connection failed!")
            return False
    except Exception as e:
        st.error(f"❌ {label} connection error: {str(e)}")
        return False


def show_configuration_summary(source_config: DatabaseConfig, dest_config: DatabaseConfig):
    """
    Display a summary of current configuration.
    
    Args:
        source_config: Source database configuration
        dest_config: Destination database configuration
    """
    with st.expander("📋 Configuration Summary", expanded=True):
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**🔗 Source Database**")
            st.markdown("""
            <div class="sql-content-container" style="max-height: 200px;">
            """, unsafe_allow_html=True)
            st.code(f"""
Host: {source_config.host}
Port: {source_config.port}
User: {source_config.user}
Schema: {source_config.schema}
Password: {'***' if source_config.password else 'Not set'}
            """)
            st.markdown("</div>", unsafe_allow_html=True)
        
        with col2:
            st.markdown("**🎯 Destination Database**")
            st.markdown("""
            <div class="sql-content-container" style="max-height: 200px;">
            """, unsafe_allow_html=True)
            st.code(f"""
Host: {dest_config.host}
Port: {dest_config.port}
User: {dest_config.user}
Schema: {dest_config.schema}
Password: {'***' if dest_config.password else 'Not set'}
            """)
            st.markdown("</div>", unsafe_allow_html=True)
        
        # Additional settings
        output_dir = getattr(st.session_state, 'output_dir', './ddl_output')
        skip_safety = getattr(st.session_state, 'skip_safety_checks', False)
        enable_viz = getattr(st.session_state, 'enable_visualization', True)
        
        st.markdown("**⚙️ Migration Settings**")
        st.markdown("""
        <div class="sql-content-container" style="max-height: 150px;">
        """, unsafe_allow_html=True)
        st.code(f"""
Output Directory: {output_dir}
Skip Safety Checks: {skip_safety}
Enable Visualization: {enable_viz}
        """)
        st.markdown("</div>", unsafe_allow_html=True)


def run_migration_analysis():
    """
    Execute the migration analysis with proper error handling and progress display.
    """
    source_config = st.session_state.source_config
    dest_config = st.session_state.dest_config
    output_dir = getattr(st.session_state, 'output_dir', './ddl_output')
    skip_safety_checks = getattr(st.session_state, 'skip_safety_checks', False)
    enable_visualization = getattr(st.session_state, 'enable_visualization', True)
    
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
        
        # Success message and tab navigation hint
        st.success("🎉 Migration analysis completed! Check the **Results** tab to review generated files and warnings.")
        
    except Exception as e:
        st.error(f"❌ Migration failed: {str(e)}")
        st.error("**Error Details:**")
        st.code(traceback.format_exc())
        
        st.session_state.last_migration_successful = False
        
    finally:
        progress_bar.empty()
        status_text.empty()


def create_connection_management_page():
    """
    Create a dedicated page for connection management.
    """
    st.markdown("Organize and manage your database connections for easy reuse across projects.")
    
    # Connection overview
    with st.container():
        st.subheader("📊 Connection Overview")
        
        saved_connections = st.session_state.connection_manager.list_connections()
        
        if not saved_connections:
            st.info("No saved connections yet. Save connections from the Setup tab to see them here.")
        else:
            # Display connections in a nice table
            connections_data = []
            for name, info in saved_connections.items():
                connections_data.append({
                    "Name": name,
                    "Host": info['host'],
                    "Port": info['port'],
                    "User": info['user'],
                    "Schema": info['schema'],
                    "Description": info.get('description', 'No description'),
                    "Last Used": info.get('last_used', 'Never')
                })
            
            # Create DataFrame for better display
            import pandas as pd
            df = pd.DataFrame(connections_data)
            st.dataframe(df, width='stretch')
    
    st.markdown("---")
    
    # Connection management actions
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📤 Export/Import")
        
        # Export
        if st.button("📤 Export All Connections", help="Export all connections to a JSON file"):
            export_path = "ddlwizard_connections_export.json"
            if st.session_state.connection_manager.export_connections(export_path):
                st.success(f"✅ Exported to {export_path}")
                with open(export_path, 'r') as f:
                    st.download_button(
                        "⬇️ Download Export File",
                        f.read(),
                        file_name=export_path,
                        mime="application/json"
                    )
            else:
                st.error("❌ Export failed")
        
        # Import
        st.markdown("**📥 Import Connections**")
        uploaded_file = st.file_uploader(
            "Choose JSON file",
            type=['json'],
            help="Upload a previously exported connections file"
        )
        
        if uploaded_file:
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp_file:
                tmp_file.write(uploaded_file.read().decode('utf-8'))
                imported_count = st.session_state.connection_manager.import_connections(tmp_file.name)
                if imported_count > 0:
                    st.success(f"✅ Imported {imported_count} connections")
                    st.rerun()
                else:
                    st.error("❌ No connections imported")
            os.unlink(tmp_file.name)
    
    with col2:
        st.subheader("🗑️ Connection Management")
        
        if saved_connections:
            # Delete connections
            st.markdown("**Delete Connection**")
            connection_to_delete = st.selectbox(
                "Select connection to delete:",
                list(saved_connections.keys()),
                help="Choose a connection to permanently delete"
            )
            
            if st.button("🗑️ Delete Selected Connection", type="secondary"):
                if st.session_state.connection_manager.delete_connection(connection_to_delete):
                    st.success(f"✅ Deleted '{connection_to_delete}'")
                    st.rerun()
                else:
                    st.error(f"❌ Failed to delete '{connection_to_delete}'")
            
            # Clear all connections
            st.markdown("---")
            st.markdown("**⚠️ Danger Zone**")
            if st.button("🗑️ Delete ALL Connections", type="secondary", help="This will permanently delete all saved connections"):
                # Confirmation
                if st.checkbox("I understand this will delete ALL connections permanently"):
                    for name in list(saved_connections.keys()):
                        st.session_state.connection_manager.delete_connection(name)
                    st.success("✅ All connections deleted")
                    st.rerun()
        else:
            st.info("No connections to manage")
    
    st.markdown("---")
    
    # Quick connection creation
    with st.container():
        st.subheader("➕ Quick Add Connection")
        st.markdown("Create a new connection directly from this page.")
        
        with st.form("quick_connection"):
            col1, col2 = st.columns(2)
            
            with col1:
                quick_name = st.text_input("Connection Name")
                quick_host = st.text_input("Host", value="localhost")
                quick_port = st.number_input("Port", value=3306, min_value=1, max_value=65535)
            
            with col2:
                quick_user = st.text_input("Username", value="root")
                quick_schema = st.text_input("Schema/Database")
                quick_description = st.text_input("Description (optional)")
            
            if st.form_submit_button("💾 Save Connection"):
                if quick_name and quick_host and quick_user and quick_schema:
                    config = DatabaseConfig(quick_host, quick_port, quick_user, "", quick_schema)
                    success = st.session_state.connection_manager.save_connection(
                        quick_name, config, quick_description
                    )
                    if success:
                        st.success(f"✅ Connection '{quick_name}' saved!")
                        st.rerun()
                    else:
                        st.error("❌ Failed to save connection")
                else:
                    st.warning("Please fill in all required fields")


def display_sidebar_info():
    """Display information in the sidebar with tab navigation guidance."""
    with st.sidebar:
        st.title("DDL Wizard")
        st.markdown("**Database Schema Migration Tool**")
        
        st.markdown("---")
        st.markdown("### 🧭 **Navigation Guide**")
        st.markdown("""
        **🔧 Setup** - Configure databases & settings
        
        **🔄 Migration** - Generate migration files
        
        **📊 Results** - Review analysis & downloads
        
        **⚡ Execute** - Apply SQL to databases
        
        **💾 Connections** - Manage saved connections
        """)
        
        st.markdown("---")
        st.markdown("### 📋 **Quick Workflow**")
        st.markdown("""
        1. **Setup** your database connections
        2. **Migration** to generate SQL files
        3. **Results** to review and download
        4. **Execute** to apply changes
        """)
        
        st.markdown("---")
        st.markdown("### � **Tool Features:**")
        st.markdown("""
        - **Schema Comparison** - Detect differences
        - **Migration Generation** - Auto-create SQL
        - **Rollback Scripts** - Safe change reversal  
        - **Safety Analysis** - Risk warnings
        - **Connection Management** - Save & reuse
        - **File Execution** - Apply SQL directly
        - **Schema Visualization** - Documentation
        - **Migration History** - Track changes
        """)
        
        st.markdown("---")
        st.markdown("### � **Pro Tips:**")
        st.markdown("""
        - **Save connections** for frequently used databases
        - **Test connections** before running migrations
        - **Review safety warnings** carefully
        - **Use dry run first** - always validate before executing
        - **Keep backups** before applying changes
        - **Start with non-production** environments
        - **Double-check target database** in Execute tab
        - **Use destination connection** for migrations (recommended)
        """)
        
        st.markdown("---")
        
        # Quick status indicators
        if (hasattr(st.session_state, 'source_config') and hasattr(st.session_state, 'dest_config') and
            st.session_state.source_config is not None and st.session_state.dest_config is not None):
            st.markdown("### 📡 **Connection Status**")
            
            source_configured = bool(getattr(st.session_state.source_config, 'schema', None))
            dest_configured = bool(getattr(st.session_state.dest_config, 'schema', None))
            
            source_icon = "🟢" if source_configured else "🔴"
            dest_icon = "🟢" if dest_configured else "🔴"
            
            st.markdown(f"""
            {source_icon} **Source:** {'Configured' if source_configured else 'Not configured'}
            {dest_icon} **Destination:** {'Configured' if dest_configured else 'Not configured'}
            """)
            
            if st.session_state.get('migration_results'):
                st.markdown("🟢 **Migration:** Generated")
            else:
                st.markdown("🔴 **Migration:** Not generated")
        else:
            st.markdown("### 📡 **Connection Status**")
            st.markdown("""
            🔴 **Source:** Not configured
            🔴 **Destination:** Not configured
            🔴 **Migration:** Not generated
            """)
        
        st.markdown("---")
        
        # Quick actions
        st.markdown("### ⚡ **Quick Actions**")
        
        if st.button("🔄 Refresh All", help="Refresh the entire application"):
            # Clear relevant session state to force refresh
            keys_to_clear = ['migration_results', 'execution_results', 'last_migration_successful']
            for key in keys_to_clear:
                if key in st.session_state:
                    del st.session_state[key]
            st.rerun()
        
        if st.button("📋 Export Logs", help="Download application logs"):
            # Check if log file exists
            log_file = "ddl_wizard.log"
            if os.path.exists(log_file):
                with open(log_file, 'r') as f:
                    log_content = f.read()
                st.download_button(
                    "⬇️ Download Logs",
                    log_content,
                    file_name=f"ddl_wizard_logs_{st.session_state.get('current_timestamp', 'export')}.log",
                    mime="text/plain"
                )
            else:
                st.info("No log file found")
        
        st.markdown("---")
        st.markdown("""
        <div style='text-align: center; color: #666; font-size: 0.8em;'>
            <p><strong>DDL Wizard v2.0</strong></p>
            <p>🚀 Tab-based Interface</p>
            <p>💾 Connection Management</p>
            <p>⚡ SQL Execution</p>
        </div>
        """, unsafe_allow_html=True)


def main():
    """Main Streamlit application with tab-based navigation."""
    initialize_session_state()
    display_sidebar_info()
    
    # Main navigation tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "🔧 Setup", 
        "🔄 Migration", 
        "📊 Results", 
        "⚡ Execute", 
        "💾 Connections"
    ])
    
    # ==================== TAB 1: SETUP ====================
    with tab1:
        st.header("🔧 Database Setup & Configuration")
        st.markdown("Configure your source and destination databases, and set migration preferences.")
        
        # Database configurations in clean sections
        with st.container():
            st.subheader("🗄️ Database Connections")
            
            col1, col2 = st.columns(2)
            
            with col1:
                source_config = create_database_config_form("source", "Source")
                st.session_state.source_config = source_config
            
            with col2:
                dest_config = create_database_config_form("dest", "Destination")
                st.session_state.dest_config = dest_config
        
        # Migration settings in separate section
        st.markdown("---")
        with st.container():
            st.subheader("⚙️ Migration Settings")
            output_dir, skip_safety_checks, enable_visualization = create_migration_settings()
            # Store settings in session state
            st.session_state.output_dir = output_dir
            st.session_state.skip_safety_checks = skip_safety_checks
            st.session_state.enable_visualization = enable_visualization
        
        # Quick validation section
        st.markdown("---")
        with st.container():
            st.subheader("✅ Configuration Validation")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if st.button("🔍 Test All Connections", type="secondary"):
                    # Test both connections
                    source_ok = test_database_connection(source_config, "Source")
                    dest_ok = test_database_connection(dest_config, "Destination")
                    
                    if source_ok and dest_ok:
                        st.success("✅ All connections working!")
                    else:
                        st.error("❌ Some connections failed - check configuration")
            
            with col2:
                if st.button("� Show Configuration Summary"):
                    show_configuration_summary(source_config, dest_config)
            
            with col3:
                if st.button("🔄 Clear All Settings"):
                    # Clear session state
                    for key in list(st.session_state.keys()):
                        if key.startswith(('source_', 'dest_', 'migration_')):
                            del st.session_state[key]
                    st.success("Settings cleared! Please refresh the page.")
    
    # ==================== TAB 2: MIGRATION ====================
    with tab2:
        st.header("🔄 Schema Migration Analysis")
        st.markdown("Generate migration and rollback scripts by comparing your database schemas.")
        
        # Migration workflow
        if not (hasattr(st.session_state, 'source_config') and hasattr(st.session_state, 'dest_config') and
                st.session_state.source_config is not None and st.session_state.dest_config is not None):
            st.warning("⚠️ Please configure databases in the **Setup** tab first.")
            return
        
        # Current configuration display
        with st.container():
            st.subheader("📋 Current Configuration")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                source_info = "Not configured"
                if st.session_state.source_config and hasattr(st.session_state.source_config, 'schema'):
                    source_info = f"{st.session_state.source_config.user}@{st.session_state.source_config.host}:{st.session_state.source_config.port}/{st.session_state.source_config.schema}"
                st.info(f"**Source:** {source_info}")
            
            with col2:
                dest_info = "Not configured"
                if st.session_state.dest_config and hasattr(st.session_state.dest_config, 'schema'):
                    dest_info = f"{st.session_state.dest_config.user}@{st.session_state.dest_config.host}:{st.session_state.dest_config.port}/{st.session_state.dest_config.schema}"
                st.info(f"**Destination:** {dest_info}")
            
            with col3:
                output_dir = getattr(st.session_state, 'output_dir', './ddl_output')
                st.info(f"**Output:** {output_dir}")
        
        st.markdown("---")
        
        # Migration execution
        with st.container():
            st.subheader("� Generate Migration")
            
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.markdown("""
                **This will:**
                - Compare source and destination schemas
                - Generate migration SQL to sync destination with source
                - Create rollback SQL to revert changes
                - Perform safety analysis and generate warnings
                - Create detailed migration report
                """)
            
            with col2:
                if st.button("🔄 Generate Migration", type="primary", help="Analyze schemas and generate migration files"):
                    run_migration_analysis()
    
    # ==================== TAB 3: RESULTS ====================
    with tab3:
        st.header("📊 Migration Results & Analysis")
        st.markdown("Review generated migration files, safety warnings, and detailed comparison results.")
        
        if st.session_state.migration_results and st.session_state.last_migration_successful:
            display_migration_results(st.session_state.migration_results)
        else:
            st.info("🔍 No migration results available. Generate a migration in the **Migration** tab first.")
    
    # ==================== TAB 4: EXECUTE ====================
    with tab4:
        st.header("⚡ Execute Migration Files")
        st.markdown("Apply migration or rollback SQL files to your databases.")
        
        create_sql_execution_section()
    
    # ==================== TAB 5: CONNECTIONS ====================
    with tab5:
        st.header("💾 Connection Management")
        st.markdown("Manage, save, and organize your database connections for easy reuse.")
        
        create_connection_management_page()
    
    # Footer
    st.markdown("---")
    with st.container():
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.markdown("""
            <div style='text-align: center; color: #666;'>
                <p>DDL Wizard v2.0 - Database Schema Migration Tool</p>
                <p>Built with ❤️ using Streamlit</p>
            </div>
            """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
