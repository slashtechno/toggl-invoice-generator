from datetime import datetime, timedelta
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
        
        response = self.client.get("api/v9/me/time_entries", params={"start_date": start_date, "end_date": end_date, "meta": True})
        time_entries = [TimeEntry.model_validate(entry) for entry in response.json()]
        # json.dump(response.json(), open("cached.json", "w"))

        # For now, load from cached.json since the free Toggl API has a really low rate limit
        # with open("cached.json", "r") as f:
            # time_entries = json.load(f)
        # time_entries = [TimeEntry.model_validate(entry) for entry in time_entries]


        # Remove any time entries that are from the next day
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



