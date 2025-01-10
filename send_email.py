import smtplib
from email.mime.text import MIMEText

def send_email(to_email, subject, body):
    # Outlook SMTP server details
    SMTP_SERVER = "mail.nexright.com"
    SMTP_PORT = 587
    EMAIL = "demo@nexright.com"
    PASSWORD = "demo@nexright"

    # Create the email
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = EMAIL
    msg["To"] = to_email

    # Send the email
    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
        server.starttls()
        server.login(EMAIL, PASSWORD)
        server.sendmail(EMAIL, [to_email], msg.as_string())

# Example usage
send_email("saurav.mishra@advintek.com.sg", "Jira Ticket Updated", "The ticket has been updated.")