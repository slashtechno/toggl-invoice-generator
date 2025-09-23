from datetime import datetime, timedelta, timezone
import json
import httpx
from pydantic import computed_field
from pydantic.main import BaseModel
from toggl_invoice_generator.config import Settings


class TimeEntry(BaseModel):
    client_name: str
    duration: int # in seconds
    project_name: str
    project_id: int 
    start: datetime
    stop: datetime

    @computed_field
    @property
    def hours(self) -> float:
        """Seconds converted to hours, rounded to 2 decimal places"""
        return round(self.duration / 3600, 2)

class TogglClient:
    def __init__(self):
        auth = httpx.BasicAuth(username=Settings().toggl_api_key, password="api_token")
        # self.client = httpx.Client(base_url="https://api.toggl.com/api/v9", auth=auth)
        self.client = httpx.Client(base_url="https://api.toggl.com", auth=auth)

    def get_time_entries(self, start_date: str = None, end_date: str = None) -> list[dict]:
        """
        Get time entries for a given date range

        Args:
            start_date: Start date in YYYY-MM-DD format (defaults to 30 days ago)
            end_date: End date in YYYY-MM-DD format (defaults to today)

        Returns:
            List of time entries
        """
        if start_date is None:
            start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        if end_date is None:
            # Use tomorrow's date to ensure we include all of today's entries (if, for whatever reason, projects from the next day show up, remove them later)
            end_date = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        
        # Add buffer to handle timezone issues and entries that span dates
        api_start_date = start_date
        api_end_date = end_date
        
        if start_date is not None:
            start_date_obj = datetime.strptime(start_date, "%Y-%m-%d")
            api_start_date = (start_date_obj - timedelta(days=1)).strftime("%Y-%m-%d")
        
        if end_date is not None:
            end_date_obj = datetime.strptime(end_date, "%Y-%m-%d")
            api_end_date = (end_date_obj + timedelta(days=2)).strftime("%Y-%m-%d")
        
        response = self.client.get("api/v9/me/time_entries", params={"start_date": api_start_date, "end_date": api_end_date, "meta": True})
        print(f"DEBUG: Response: {json.dumps(response.json(), indent=2) }") # format the json nicely
        time_entries = [TimeEntry.model_validate(entry) for entry in response.json()]


        # Filter entries based on the original date range to handle timezone issues
        if start_date is not None:
            start_date_obj = datetime.strptime(start_date, "%Y-%m-%d").replace(hour=0, minute=0, second=0, tzinfo=timezone.utc)
            time_entries = [entry for entry in time_entries if entry.start >= start_date_obj]
        
        if end_date is not None:
            # Include entries that start on or before the end_date, plus entries that start on the next day
            # This handles timezone edge cases where work done on end_date appears as next day in UTC
            next_day_obj = (datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)).replace(hour=23, minute=59, second=59, tzinfo=timezone.utc)
            time_entries = [entry for entry in time_entries if entry.start <= next_day_obj]
        
        # If no explicit dates provided, use default filtering
        if start_date is None and end_date is None:
            time_entries = [entry for entry in time_entries if entry.start.date() <= datetime.now().date()]
            time_entries = [entry for entry in time_entries if entry.stop.date() <= datetime.now().date()]

        return time_entries

    def download_report(self, workspace_id: int, start_date: str=None, end_date: str=None, project_ids: list[int]=None, filename: str= f"toggl_report_{datetime.now().strftime('%Y-%m-%d')}.pdf") -> None:

        """
        Download a report from Toggl and export it to a PDF file
        """

        if start_date is None:
            start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        if end_date is None:
            end_date = datetime.now().strftime("%Y-%m-%d")
            # Use tomorrow's date to ensure we include all of today's entries (if, for whatever reason, projects from the next day show up, remove them later)
            # end_date = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
        
        response = self.client.post(f"reports/api/v3/workspace/{workspace_id}/search/time_entries.pdf", json={"start_date": start_date, "end_date": end_date, "project_ids": project_ids})
        # response = httpx.post(f"https://api.track.toggl.com/reports/api/v3/workspace/{workspace_id}/search/time_entries.pdf", json={"start_date": start_date, "end_date": end_date, "project_ids": project_ids}, auth=self.client.auth)
        if response.status_code == 200:
            with open(filename, "wb") as f:
                f.write(response.content)
        else:
            raise Exception(f"Failed to download report: {response.status_code} {response.text}")



