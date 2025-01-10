import imaplib
import email
from email.header import decode_header

# Configuration
IMAP_SERVER = "mail.nexright.com"
EMAIL = "demo@nexright.com"
PASSWORD = "demo@nexright"

class Email:
    def __init__(self, subject, sender, body, cc=None, bcc=None, attachments=0):
        self.subject = subject
        self.sender = sender
        self.body = body
        self.cc = cc
        self.bcc = bcc
        self.attachments = attachments

    def __str__(self):
        """Returns a detailed string representation of the email."""
        email_str = f"Subject: {self.subject}\n"
        email_str += f"From: {self.sender}\n"
        if self.cc:
            email_str += f"CC: {self.cc}\n"
        if self.bcc:
            email_str += f"BCC: {self.bcc}\n"
        email_str += f"Body: {self.body[:100]}...\n"  # Truncate body for display
        email_str += f"Attachments: {self.attachments}\n"
        return email_str

class EmailProcessor:
    def __init__(self):
        self.seen_count = 0
        self.unseen_count = 0
        self.processed_count = 0
        self.emails = []

    def fetch_unread_emails(self):
        try:
            # Connect to the IMAP server
            mail = imaplib.IMAP4_SSL(IMAP_SERVER)
            mail.login(EMAIL, PASSWORD)
            mail.select("Inbox")  # Select the inbox folder

            # Search for unread emails
            status, messages = mail.search(None, "UNSEEN")
            if status != "OK":
                print("No unread emails found.")
                return

            email_ids = messages[0].split()
            self.unseen_count = len(email_ids)

            for email_id in email_ids:
                try:
                    # Fetch the email by ID
                    status, msg_data = mail.fetch(email_id, "(RFC822)")
                    for response_part in msg_data:
                        if isinstance(response_part, tuple):
                            msg = email.message_from_bytes(response_part[1])

                            # Extract email details
                            subject, encoding = decode_header(msg["Subject"])[0]
                            if isinstance(subject, bytes):
                                subject = subject.decode(encoding or "utf-8")
                            from_ = msg.get("From")
                            body = self.get_email_body(msg)
                            cc = msg.get("Cc", "")
                            bcc = msg.get("Bcc", "")
                            attachments = self.count_attachments(msg)

                            # Create an Email object
                            email_obj = Email(subject, from_, body, cc, bcc, attachments)
                            self.emails.append(email_obj)

                            # Mark the email as read
                            mail.store(email_id, "+FLAGS", "\\Seen")
                            self.processed_count += 1

                except Exception as e:
                    print(f"Error processing email ID {email_id}: {e}")

            # Count seen emails
            status, messages = mail.search(None, "SEEN")
            if status == "OK":
                self.seen_count = len(messages[0].split())

        except imaplib.IMAP4.error as e:
            print(f"IMAP error: {e}")
        except Exception as e:
            print(f"Unexpected error: {e}")
        finally:
            try:
                mail.logout()
            except:
                pass

    def get_email_body(self, msg):
        """Extract the email body from the message."""
        body = ""
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                if content_type == "text/plain":
                    body = part.get_payload(decode=True).decode("utf-8")
                    break
        else:
            body = msg.get_payload(decode=True).decode("utf-8")
        return body

    def count_attachments(self, msg):
        """Count the number of attachments in the email."""
        attachments = 0
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_maintype() == "multipart":
                    continue
                if part.get("Content-Disposition") is not None:
                    attachments += 1
        return attachments

    def print_stats(self):
        """Print statistics about seen, unseen, and processed emails."""
        print(f"Unseen Emails: {self.unseen_count}")
        print(f"Seen Emails: {self.seen_count}")
        print(f"Processed Emails: {self.processed_count}")

    def print_processed_emails(self):
        """Print all processed emails in a structured format."""
        if not self.emails:
            print("No emails processed.")
            return

        print("\nProcessed Emails:")
        print("=" * 50)
        for idx, email_obj in enumerate(self.emails, start=1):
            print(f"Email #{idx}:")
            print(email_obj)
            print("-" * 50)

# Example usage
if __name__ == "__main__":
    processor = EmailProcessor()
    processor.fetch_unread_emails()
    processor.print_stats()
    processor.print_processed_emails()