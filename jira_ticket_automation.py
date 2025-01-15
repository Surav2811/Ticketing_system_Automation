import time
import schedule
import logging
from read_email import EmailProcessor
from create_ticket import create_jira_ticket
from send_email import send_email
import os
from dotenv import load_dotenv

load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("email_jira_automation.log"),
        logging.StreamHandler()
    ]
)

def job():
    """Fetch unread emails, create Jira tickets, and send notifications."""
    try:
        processor = EmailProcessor()
        processor.fetch_unread_emails()

        # Check if there are unread emails
        if processor.unseen_count > 0:
            logging.info(f"Found {processor.unseen_count} unread email(s). Processing...")
            for email in processor.emails:
                try:
                    # Use email subject as ticket summary and body as description
                    issue_dict = {
                        "project": os.getenv("JIRA_PROJECT_KEY"),  # Replace with your project key
                        "summary": email.subject,  # Use email subject as ticket summary
                        "description": email.body,  # Use email body as ticket description
                        "issuetype": os.getenv("JIRA_ISSUE_TYPE"),  # Replace with your issue type
                    }

                    # Create a Jira ticket and pass attachments
                    issue_key = create_jira_ticket(issue_dict, email.attachments)
                    
                    if issue_key:
                        # Send an email notification with the Jira ticket details
                        subject = f"Jira Ticket Created: {issue_key}"
                        body = f"A new Jira ticket has been created for your email.\n\nSubject: {email.subject}\nTicket Key: {issue_key}"
                        send_email(email.sender, subject, body)
                        logging.info(f"Successfully created Jira ticket {issue_key} and sent notification to {email.sender}.")
                    else:
                        logging.error(f"Failed to create Jira ticket for email from {email.sender}.")
                
                except Exception as e:
                    logging.error(f"Error processing email from {email.sender}: {e}", exc_info=True)
        else:
            logging.info("No unread emails found. Skipping Jira ticket creation.")

        processor.print_stats()
        processor.print_processed_emails()

    except Exception as e:
        logging.error(f"Unexpected error in job execution: {e}", exc_info=True)

# Schedule the job to run every 5 minutes
schedule.every(2).minutes.do(job)

# Keep the script running
while True:
    try:
        schedule.run_pending()
        time.sleep(1)
    except KeyboardInterrupt:
        logging.info("Program terminated by user.")
        break
    except Exception as e:
        logging.error(f"Unexpected error in scheduler: {e}", exc_info=True)

# if __name__ == "__main__":
#     job()
