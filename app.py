import streamlit as st
from jira_ticket_automation import JiraTicketAutomation
from email_processing_dashboard import EmailProcessingDashboard
import logging
import threading
import time
import os
import signal
import atexit

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def cleanup():
    """Cleanup function for graceful shutdown"""
    logging.info("Cleaning up resources...")
    if st.session_state.get('automation_instance'):
        st.session_state.automation_instance.stop()

def main():
    # Register cleanup handler
    atexit.register(cleanup)
    
    st.set_page_config(page_title="Email Processing Dashboard", layout="wide")
    
    # Initialize session state
    if 'dashboard' not in st.session_state:
        st.session_state.dashboard = EmailProcessingDashboard()
    if 'automation_running' not in st.session_state:
        st.session_state.automation_running = False
    if 'automation_instance' not in st.session_state:
        st.session_state.automation_instance = None

    dashboard = st.session_state.dashboard
    
    # Create the interface
    st.title("Email Processing Dashboard")

    # Status indicator in sidebar
    status = "🟢 Running" if st.session_state.automation_running else "🔴 Stopped"
    st.sidebar.markdown(f"### Status: {status}")
    
    # Add refresh rate selector in sidebar
    refresh_rate = st.sidebar.slider("Refresh Rate (seconds)", 1, 10, 5)
    st.sidebar.markdown("---")

    # Control buttons
    col1, col2 = st.columns(2)
    with col1:
        if not st.session_state.automation_running:
            if st.button("Start Automation"):
                try:
                    automation = JiraTicketAutomation(dashboard)
                    st.session_state.automation_instance = automation
                    
                    monitor_thread = threading.Thread(
                        target=automation.monitor_inbox,
                        daemon=True
                    )
                    monitor_thread.start()
                    
                    st.session_state.automation_running = True
                    st.success("Automation started successfully!")
                    time.sleep(1)
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to start automation: {str(e)}")
                    logging.error(f"Failed to start automation: {e}")

    with col2:
        if st.session_state.automation_running:
            if st.button("Stop Automation"):
                try:
                    if st.session_state.automation_instance:
                        with st.spinner('Stopping automation service...'):
                            st.session_state.automation_instance.stop()
                            st.session_state.automation_instance = None
                            st.session_state.automation_running = False
                            
                        st.success("Automation stopped successfully!")
                        time.sleep(1)
                        st.rerun()
                        
                except Exception as e:
                    error_msg = f"Failed to stop automation: {str(e)}"
                    st.error(error_msg)
                    logging.error(error_msg)

    # Statistics cards
    st.markdown("---")
    st.subheader("Processing Statistics")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Emails Processed", dashboard.get_processed_count())
    with col2:
        st.metric("Errors", dashboard.get_error_count(), delta_color="inverse")
    with col3:
        st.metric("Queue Size", dashboard.email_queue.qsize())
    with col4:
        st.metric("Success Rate (%)", dashboard.calculate_success_rate())

    # Status table
    st.markdown("---")
    st.subheader("Processing Status")
    status_df = dashboard.get_status_df()
    if not status_df.empty:
        # Add color coding for status
        def highlight_status(row):
            if row['Status'] == 'Completed':
                return ['background-color: #90EE90'] * len(row)
            elif row['Status'] == 'Failed':
                return ['background-color: #FFB6C1'] * len(row)
            return [''] * len(row)

        st.dataframe(
            status_df.style.apply(highlight_status, axis=1),
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("No emails processed yet")

    # Auto-refresh
    time.sleep(refresh_rate)
    st.rerun()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        cleanup()
        logging.info("Application stopped by user") 