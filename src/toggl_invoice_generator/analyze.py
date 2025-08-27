from pydantic import BaseModel, computed_field

from toggl_invoice_generator.config import Project
from toggl_invoice_generator.toggl import TimeEntry

class ProjectSummary(BaseModel):
    project: Project
    hours: float
    entries: list[TimeEntry]
    
    @computed_field
    @property
    def total_revenue(self) -> float:
        return self.hours * self.project.hourly_rate

    @computed_field
    @property
    def hour_minute_format(self) -> str:
        hours = int(self.hours)
        minutes = int((self.hours - hours) * 60)
        return f"{hours}h {minutes}m"

    @computed_field
    @property
    def short_summary(self) -> str:
        return f"{self.project.name} - {self.hour_minute_format} - {self.total_revenue:.2f}"

def summarize_time_entries(time_entries: list[TimeEntry], projects: list[Project]) -> list[ProjectSummary]:
    summaries = []
    for project in projects:
        hours = sum(time_entry.hours for time_entry in time_entries if (time_entry.project_id == project.project_id))
        total_revenue = hours * project.hourly_rate
        summaries.append(ProjectSummary(project=project, hours=hours, total_revenue=total_revenue, entries=time_entries))
    return summaries
