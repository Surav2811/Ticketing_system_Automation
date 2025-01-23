import pandas as pd
from datetime import datetime
import queue
import threading
import logging

class EmailProcessingDashboard:
    def __init__(self):
        self.email_queue = queue.Queue()
        self.processing_status = {}
        self.lock = threading.Lock()
        self.should_run = True

    def update_status(self, email_id, status, details=""):
        """Update status for an email"""
        with self.lock:
            self.processing_status[email_id] = {
                "status": status,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "details": details
            }
            logging.info(f"Status updated for {email_id}: {status} - {details}")

    def get_status_df(self):
        """Get current status as a DataFrame"""
        with self.lock:
            if not self.processing_status:
                return pd.DataFrame(columns=["Email ID", "Status", "Timestamp", "Details"])
            
            data = [
                {
                    "Email ID": email_id,
                    "Status": info["status"],
                    "Timestamp": info["timestamp"],
                    "Details": info["details"]
                }
                for email_id, info in self.processing_status.items()
            ]
            return pd.DataFrame(data)

    def get_processed_count(self):
        """Get count of processed emails"""
        with self.lock:
            return len([s for s in self.processing_status.values() if s["status"] == "Completed"])

    def get_error_count(self):
        """Get count of errored emails"""
        with self.lock:
            return len([s for s in self.processing_status.values() if s["status"] == "Failed"])

    def calculate_success_rate(self):
        """Calculate success rate percentage"""
        with self.lock:
            completed = len([s for s in self.processing_status.values() if s["status"] == "Completed"])
            total = len([s for s in self.processing_status.values() if s["status"] in ["Completed", "Failed"]])
            return round((completed / total * 100) if total > 0 else 100, 2)

    def cleanup(self):
        """Cleanup resources and log final status"""
        with self.lock:
            self.should_run = False
            total_processed = self.get_processed_count()
            total_errors = self.get_error_count()
            success_rate = self.calculate_success_rate()
            logging.info(f"Dashboard cleanup - Total processed: {total_processed}, Errors: {total_errors}, Success rate: {success_rate}%")
