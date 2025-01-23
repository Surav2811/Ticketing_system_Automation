import pytest
from unittest.mock import MagicMock
import streamlit as st
from app import main, cleanup
from email_processing_dashboard import EmailProcessingDashboard
from jira_ticket_automation import JiraTicketAutomation

@pytest.fixture
def setup_streamlit():
    """Fixture to set up Streamlit session state."""
    st.session_state.clear()
    st.session_state.dashboard = EmailProcessingDashboard()
    st.session_state.automation_running = False
    st.session_state.automation_instance = None

def test_initialization(setup_streamlit):
    """Test that the application initializes the session state correctly."""
    main()
    assert 'dashboard' in st.session_state
    assert isinstance(st.session_state.dashboard, EmailProcessingDashboard)
    assert st.session_state.automation_running is False
    assert st.session_state.automation_instance is None

def test_start_automation(setup_streamlit, mocker):
    """Test the start automation functionality."""
    mock_dashboard = MagicMock()
    mocker.patch('app.EmailProcessingDashboard', return_value=mock_dashboard)
    mock_jira_instance = MagicMock()
    mocker.patch('app.JiraTicketAutomation', return_value=mock_jira_instance)

    st.session_state.dashboard = mock_dashboard
    st.session_state.automation_running = False

    # Simulate button click
    with st.spinner("Starting automation..."):
        st.session_state.automation_instance = mock_jira_instance
        st.session_state.automation_running = True

    assert st.session_state.automation_running is True
    mock_jira_instance.monitor_inbox.assert_called_once()

def test_stop_automation(setup_streamlit, mocker):
    """Test the stop automation functionality."""
    mock_jira_instance = MagicMock()
    st.session_state.automation_instance = mock_jira_instance
    st.session_state.automation_running = True

    with st.spinner("Stopping automation..."):
        cleanup()
        st.session_state.automation_instance.stop()
        st.session_state.automation_instance = None
        st.session_state.automation_running = False

    assert st.session_state.automation_running is False
    mock_jira_instance.stop.assert_called_once()

def test_dashboard_statistics(setup_streamlit):
    """Test the dashboard statistics calculations."""
    dashboard = st.session_state.dashboard
    dashboard.update_status("email_1", "Completed")
    dashboard.update_status("email_2", "Failed")

    assert dashboard.get_processed_count() == 1
    assert dashboard.get_error_count() == 1
    assert dashboard.calculate_success_rate() == 50.0

def test_email_processing(mocker):
    """Test the email processing logic in JiraTicketAutomation."""
    mock_dashboard = MagicMock()
    mock_jira_instance = JiraTicketAutomation(mock_dashboard)

    # Mock email data
    mock_email = MagicMock()
    mock_email.subject = "Test email"
    mock_email.body = "This is a test email body."
    mock_email.sender = "test@example.com"
    mock_email.attachments = []

    # Simulate processing the email
    mock_jira_instance.process_new_email(mock_email)

    # Check that the dashboard status was updated
    mock_dashboard.update_status.assert_called()