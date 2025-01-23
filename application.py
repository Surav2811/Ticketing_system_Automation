import streamlit as st
from jira_ticket_automation import JiraTicketAutomation
from email_processing_dashboard import EmailProcessingDashboard
import logging
import threading
import time
import atexit

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Module-level variables for cleanup
_automation_instance = None

def cleanup():
    """Cleanup function for graceful shutdown"""
    logging.info("Cleaning up resources...")
    global _automation_instance
    if _automation_instance is not None:
        try:
            _automation_instance.stop()
            _automation_instance = None
        except Exception as e:
            logging.error(f"Error during cleanup: {str(e)}")

atexit.register(cleanup)

def main():
    global _automation_instance
    st.set_page_config(page_title="Email Processing Dashboard", layout="wide")
    
    # Initialize session state
    if 'dashboard' not in st.session_state:
        st.session_state.dashboard = EmailProcessingDashboard()
    if 'automation_running' not in st.session_state:
        st.session_state.automation_running = False

    dashboard = st.session_state.dashboard
    
    # Create the interface
    st.title("Email Processing Dashboard")

    # Status indicator
    status = "🟢 Running" if st.session_state.automation_running else "🔴 Stopped"
    st.sidebar.markdown(f"### Status: {status}")
    
    # Refresh rate control
    refresh_rate = st.sidebar.slider("Refresh Rate (seconds)", 1, 10, 5)
    st.sidebar.markdown("---")

    # Control buttons
    col1, col2 = st.columns(2)
    with col1:
        if not st.session_state.automation_running:
            if st.button("Start Automation"):
                try:
                    _automation_instance = JiraTicketAutomation(dashboard)
                    monitor_thread = threading.Thread(
                        target=_automation_instance.monitor_inbox,
                        daemon=True
                    )
                    monitor_thread.start()
                    st.session_state.automation_running = True
                    st.success("Automation started!")
                    time.sleep(1)
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to start automation: {str(e)}")
                    logging.error(f"Start automation error: {e}")

    with col2:
        if st.session_state.automation_running:
            if st.button("Stop Automation"):
                try:
                    if _automation_instance:
                        with st.spinner('Stopping...'):
                            cleanup()  # Call cleanup directly
                            st.session_state.automation_running = False
                        st.success("Automation stopped!")
                        time.sleep(1)
                        st.rerun()
                except Exception as e:
                    st.error(f"Failed to stop automation: {str(e)}")
                    logging.error(f"Stop automation error: {e}")

    # Statistics
    st.markdown("---")
    st.subheader("Processing Statistics")
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Emails Processed", dashboard.get_processed_count())
    col2.metric("Errors", dashboard.get_error_count(), delta_color="inverse")
    col3.metric("Queue Size", dashboard.email_queue.qsize())
    col4.metric("Success Rate (%)", dashboard.calculate_success_rate())

    # Status table
    st.markdown("---")
    st.subheader("Processing Status")
    status_df = dashboard.get_status_df()
    if not status_df.empty:
        def highlight_status(row):
            color = '#90EE90' if row['Status'] == 'Completed' else '#FFB6C1'
            return [f'background-color: {color}'] * len(row)
        st.dataframe(
            status_df.style.apply(highlight_status, axis=1),
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("No emails processed yet")

    # Auto-refresh only if automation is active
    if st.session_state.automation_running:
        time.sleep(refresh_rate)
        st.rerun()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logging.info("Application stopped by user")