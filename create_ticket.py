from jira import JIRA
from dotenv import load_dotenv
import os

load_dotenv()

def create_jira_ticket(issue_dict, attachments):
    """Create a Jira ticket with the given issue details and attachments."""
    try:
         # Jira configuration from .env
        JIRA_SERVER = os.getenv("JIRA_SERVER")
        JIRA_EMAIL = os.getenv("JIRA_EMAIL")
        JIRA_API_TOKEN = os.getenv("JIRA_API_TOKEN")

        # Initialize Jira connection
        jira = JIRA(JIRA_SERVER, basic_auth=(JIRA_EMAIL, JIRA_API_TOKEN))

        # Create the issue
        issue = jira.create_issue(fields=issue_dict)

        # Add attachments if any
        for attachment in attachments:
            with open(attachment, 'rb') as file:
                jira.add_attachment(issue=issue, attachment=file)

        return issue.key

    except Exception as e:
        print(f"Error creating Jira ticket: {e}")
        return None