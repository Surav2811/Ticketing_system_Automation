import logging
from read_email import EmailProcessor
import os
from dotenv import load_dotenv
import re
from jira import JIRA
import imaplib
import email
import time
import uuid
import json
from openai import OpenAI
#import streamlit as st

load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class JiraTicketAutomation:
    def __init__(self, dashboard):
        self.email_processor = EmailProcessor()
        self.email_summarizer = EmailSummarizer()
        self.dashboard = dashboard
        self.jira_project = os.getenv("JIRA_PROJECT_KEY")
        self.issue_type = os.getenv("JIRA_ISSUE_TYPE")
        self.processed_tickets = {}
        self.imap_server = os.getenv("IMAP_SERVER")
        self.email_address = os.getenv("EMAIL")
        self.email_password = os.getenv("PASSWORD")
        self.running = True
        
        self.initialize_jira_client()
        self.initialize_imap_client()
        self.monitor_thread = None

    def initialize_jira_client(self):
        """Initialize Jira client with API credentials."""
        try:
            self.jira_server = os.getenv("JIRA_SERVER")
            self.jira_email = os.getenv("JIRA_EMAIL")
            self.jira_api_token = os.getenv("JIRA_API_TOKEN")
            
            self.jira = JIRA(
                server=self.jira_server,
                basic_auth=(self.jira_email, self.jira_api_token)
            )
            logging.info("Jira client initialized successfully")
        except Exception as e:
            logging.error(f"Failed to initialize Jira client: {e}", exc_info=True)
            raise

    def initialize_imap_client(self):
        """Initialize IMAP client for real-time email monitoring."""
        try:
            self.imap = imaplib.IMAP4_SSL(self.imap_server)
            self.imap.login(self.email_address, self.email_password)
            logging.info("IMAP client initialized successfully")
        except Exception as e:
            logging.error(f"Failed to initialize IMAP client: {e}", exc_info=True)
            raise

    def categorize_email(self, email_data):
        """Enhanced categorization with management commands"""
        subject = email_data.subject.lower()
        
        # Delete command detection
        if subject.startswith('delete ticket '):
            ticket_refs = re.findall(r'[A-Z]+-\d+', email_data.subject)
            if ticket_refs:
                return ('delete', ticket_refs[0])
                
        # Update command detection
        if subject.startswith('update ticket '):
            ticket_refs = re.findall(r'[A-Z]+-\d+', email_data.subject)
            if ticket_refs:
                return ('update', ticket_refs[0])
        
        # Skip notifications
        notification_phrases = ['jira ticket', 'ticket created', 'issue updated']
        if any(phrase in subject for phrase in notification_phrases):
            return 'notification'
        
        # Spam detection
        spam_keywords = ['spam', 'promotion', 'offer', 'deal']
        if any(keyword in subject for keyword in spam_keywords):
            return 'spam'
            
        # Existing ticket detection
        ticket_refs = re.findall(r'[A-Z]+-\d+', email_data.subject)
        return ('existing', ticket_refs[0]) if ticket_refs else 'new'

    def create_jira_ticket(self, issue_dict, attachments):
        """Create Jira ticket with error handling."""
        try:
            issue = self.jira.create_issue(fields=issue_dict)
            if attachments:
                for attachment in attachments:
                    with open(attachment, 'rb') as file:
                        self.jira.add_attachment(issue=issue, attachment=file)
            return issue.key
        except Exception as e:
            logging.error(f"Ticket creation error: {e}", exc_info=True)
            return None

    def update_jira_ticket(self, ticket_key, email_data):
        """Update existing ticket with validation."""
        try:
            issue = self.jira.issue(ticket_key)
            comment = f"Update from {email_data.sender}:\n{email_data.body}"
            self.jira.add_comment(issue.key, comment)
            
            if email_data.attachments:
                for attachment in email_data.attachments:
                    with open(attachment, 'rb') as file:
                        self.jira.add_attachment(issue=issue, attachment=file)
            return True
        except Exception as e:
            logging.error(f"Ticket update error: {e}", exc_info=True)
            return False

    def delete_jira_ticket(self, ticket_key, email_data):
        """Delete a Jira ticket with validation"""
        try:
            if not self.is_authorized_sender(email_data.sender):
                logging.warning(f"Unauthorized deletion attempt by {email_data.sender}")
                return False
                
            issue = self.jira.issue(ticket_key)
            
            # Add audit comment before deletion
            comment = f"Ticket deletion requested by {email_data.sender} via email\n" \
                    f"Reason: {email_data.body[:200]}"
            self.jira.add_comment(issue.key, comment)
            
            # Perform deletion
            self.jira.delete_issue(issue.key)
            logging.info(f"Deleted ticket {issue.key}")
            return True
            
        except Exception as e:
            logging.error(f"Failed to delete ticket {ticket_key}: {e}", exc_info=True)
            return False

    def update_jira_issue(self, ticket_key, email_data):
        """Update Jira issue fields based on email content"""
        try:
            issue = self.jira.issue(ticket_key)
            updates = self.parse_update_instructions(email_data.body)
            
            # Build update dictionary
            fields = {}
            if 'priority' in updates:
                fields['priority'] = {'name': updates['priority']}
            if 'status' in updates:
                self.jira.transition_issue(issue, updates['status'])
                
            # Add comment with update details
            comment = f"Update from {email_data.sender} via email:\n{email_data.body[:500]}"
            self.jira.add_comment(issue.key, comment)
            
            # Update fields if any
            if fields:
                issue.update(fields=fields)
                
            # Handle attachments
            if email_data.attachments:
                for attachment in email_data.attachments:
                    with open(attachment, 'rb') as file:
                        self.jira.add_attachment(issue=issue, attachment=file)
                        
            return True
            
        except Exception as e:
            logging.error(f"Failed to update ticket {ticket_key}: {e}", exc_info=True)
            return False

    def parse_update_instructions(self, body):
        """Extract update instructions from email body"""
        updates = {}
        body_lower = body.lower()
        
        # Priority detection
        priority_map = {
            'high': 'High',
            'medium': 'Medium',
            'low': 'Low'
        }
        for p in priority_map:
            if f'priority {p}' in body_lower:
                updates['priority'] = priority_map[p]
                
        # Status detection
        status_map = {
            'resolve': 'Done',
            'close': 'Closed',
            'reopen': 'Reopened'
        }
        for s in status_map:
            if f'mark as {s}' in body_lower:
                updates['status'] = status_map[s]
                
        return updates

    def is_authorized_sender(self, sender_email):
        """Check if sender is authorized for sensitive operations"""
        authorized_users = os.getenv("AUTHORIZED_USERS", "").split(',')
        return any(auth_email.strip() in sender_email for auth_email in authorized_users)

    def process_new_email(self, email_msg):
        """Process email with enhanced error handling."""
        email_id = str(uuid.uuid4())
        try:
            email_data = self.email_processor.parse_email(email_msg)
            self.dashboard.update_status(email_id, "Processing", "Email received")
            
            category = self.categorize_email(email_data)
            
            # Handle management commands first
            if isinstance(category, tuple):
                action, ticket_key = category
                
                if action == 'delete':
                    success = self.delete_jira_ticket(ticket_key, email_data)
                    status = "Completed" if success else "Failed"
                    self.dashboard.update_status(email_id, status, f"Deleted {ticket_key}")
                    return
                        
                elif action == 'update':
                    success = self.update_jira_issue(ticket_key, email_data)
                    status = "Completed" if success else "Failed"
                    self.dashboard.update_status(email_id, status, f"Updated {ticket_key}")
                    return
                
                elif action == 'existing':
                    success = self.update_jira_ticket(ticket_key, email_data)
                    status = "Completed" if success else "Failed"
                    self.dashboard.update_status(email_id, status, f"Updated {ticket_key}")
                    return

            # Skip notifications and spam
            if category in ['notification', 'spam']:
                self.dashboard.update_status(email_id, "Skipped", f"{category.capitalize()} email")
                return

            # Process new ticket
            summary_response = self.email_summarizer.summarize_email(
                email_data.subject,
                email_data.body,
                email_data.sender,
                email_data.recipients
            )
            
            if not summary_response:
                raise ValueError("Empty summary response")
                
            summary_data = json.loads(summary_response)
            self.validate_summary_data(summary_data)
            
            # Process participants safely
            participants = [
                p.get('name', str(p)) if isinstance(p, dict) else str(p)
                for p in summary_data.get('participants', [])
            ]
            
            issue_dict = {
                "project": {"key": self.jira_project},
                "summary": email_data.subject,
                "description": self.build_description(summary_data, email_data, participants),
                "issuetype": {"name": self.issue_type},
            }
            
            issue_key = self.create_jira_ticket(issue_dict, email_data.attachments)
            if issue_key:
                self.dashboard.update_status(email_id, "Completed", f"Created {issue_key}")
            else:
                raise Exception("Ticket creation failed")

        except Exception as e:
            logging.error(f"Processing error: {e}", exc_info=True)
            self.dashboard.update_status(email_id, "Failed", str(e)[:100])

    def validate_summary_data(self, summary_data):
        """Validate summary structure and content."""
        required_keys = {
            "summary": str,
            "participants": list,
            "priority": str,
            "category": str
        }
        
        for key, expected_type in required_keys.items():
            if key not in summary_data:
                raise ValueError(f"Missing required field: {key}")
            if not isinstance(summary_data[key], expected_type):
                raise ValueError(f"Invalid type for {key}. Expected {expected_type}")
                
        if summary_data["priority"].lower() not in {"high", "medium", "low"}:
            raise ValueError("Invalid priority value")

    def build_description(self, summary_data, email_data, participants):
        """Construct Jira description safely."""
        return f"""Summary:
{summary_data['summary']}

Priority: {summary_data['priority'].title()}
Category: {summary_data['category'].title()}

Participants:
{', '.join(participants) or 'None'}

Original Email:
{email_data.body[:2000]}"""  # Limit email body length

    def monitor_inbox(self):
        """IMAP monitoring with better connection handling."""
        try:
            while self.running:
                try:
                    self.imap.select('INBOX')
                    _, messages = self.imap.search(None, 'UNSEEN')
                    
                    for msg_num in (messages[0].split() if messages[0] else []):
                        if not self.running:
                            break
                        self.process_message(msg_num)
                        
                    time.sleep(0.5)
                    
                except imaplib.IMAP4.abort:
                    self.reconnect_imap()
                    
        except Exception as e:
            logging.error(f"Monitoring error: {e}", exc_info=True)
        finally:
            logging.info("Monitoring stopped")

    def process_message(self, msg_num):
        """Process individual email message."""
        try:
            _, msg_data = self.imap.fetch(msg_num, '(RFC822)')
            email_msg = email.message_from_bytes(msg_data[0][1])
            logging.info(f"Processing: {email_msg['Subject']}")
            self.process_new_email(email_msg)
        except Exception as e:
            logging.error(f"Message processing error: {e}", exc_info=True)

    def reconnect_imap(self):
        """Reconnect IMAP with retries."""
        for attempt in range(3):
            try:
                self.initialize_imap_client()
                logging.info("IMAP reconnected successfully")
                return
            except Exception as e:
                logging.warning(f"Reconnect attempt {attempt+1}/3 failed: {e}")
                time.sleep(2)
        logging.error("Failed to reconnect IMAP after 3 attempts")

    def stop(self):
        """Improved shutdown procedure."""
        if not self.running:
            return

        logging.info("Initiating shutdown...")
        self.running = False

        # Break IMAP loop
        try:
            self.imap.noop()
        except Exception as e:
            logging.debug(f"IMAP noop error: {e}")

        # Wait for monitoring thread
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=5)
            if self.monitor_thread.is_alive():
                logging.warning("Monitor thread did not exit cleanly")

        # Close connections
        try:
            self.imap.close()
            self.imap.logout()
        except Exception as e:
            logging.debug(f"IMAP logout error: {e}")
        finally:
            self.imap = None

        logging.info("Service shutdown complete")


class EmailSummarizer:
    def __init__(self):
        load_dotenv()
        self.client = OpenAI(
            base_url=os.getenv("OPEN_AI_BASE_URL"),
            api_key=os.getenv("OPENROUTER_API_KEY"),
            timeout=30
        )
        logging.info("Summarizer initialized")

    def summarize_email(self, subject, body, sender, recipients):
        """Get summary with timeout and validation."""
        prompt = f"""Analyze this email and return JSON with:
- summary: 100-word technical summary
- participants: list of involved people (names/emails)
- priority: High/Medium/Low
- category: Technical/Business/Support/Other

Email Subject: {subject}
From: {sender}
To: {recipients}
Body: {body}"""

        try:
            response = self.client.chat.completions.create(
                model=os.getenv("MODEL_FREE"),
                messages=[{"role": "user", "content": prompt}],
                response_format={"type": "json_object"},
                temperature=0.7,
                max_tokens=500,
                timeout=30
            )
            
            if response.choices:
                return response.choices[0].message.content
            return None
            
        except Exception as e:
            logging.error(f"Summarization failed: {e}", exc_info=True)
            return None