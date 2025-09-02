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

from .utils.database import DatabaseConfig
from .utils.config import DDLWizardConfig, DatabaseConnection, DatabaseSettings, OutputSettings, SafetySettings
from .core import run_complete_migration


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


def create_database_config_form(prefix: str, label: str) -> DatabaseConfig:
    """
    Create a form for database configuration.
    
    Args:
        prefix: Prefix for form keys
        label: Display label for the form
        
    Returns:
        DatabaseConfig: Database configuration object
    """
    with st.expander(f"🗄️ {label} Database Configuration", expanded=True):
        col1, col2 = st.columns(2)
        
        with col1:
            host = st.text_input(f"Host", value="localhost", key=f"{prefix}_host")
            port = st.number_input(f"Port", min_value=1, max_value=65535, value=3306, key=f"{prefix}_port")
            username = st.text_input(f"Username", value="root", key=f"{prefix}_username")
        
        with col2:
            password = st.text_input(f"Password", type="password", key=f"{prefix}_password")
            schema = st.text_input(f"Schema/Database", key=f"{prefix}_schema")
            
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
    
    # Return config with defaults for empty fields to avoid validation errors
    return DatabaseConfig(
        host=host or "localhost", 
        port=port or 3306, 
        user=username or "root", 
        password=password or "", 
        schema=schema or "test"
    )


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
        """)
        
        st.markdown("---")
        st.markdown("### 🚀 How to use:")
        st.markdown("""
        1. Configure source database
        2. Configure destination database
        3. Set migration options
        4. Run migration analysis
        5. Download generated files
        """)
        
        st.markdown("---")
        st.markdown("### 💡 Tips:")
        st.markdown("""
        - Test connections before running
        - Enable safety analysis for production
        - Review warnings carefully
        - Keep backups before applying
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
    
    with col2:
        dest_config = create_database_config_form("dest", "Destination")
    
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
