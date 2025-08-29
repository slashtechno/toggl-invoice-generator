from toggl_invoice_generator.invoice import create_invoice_from_summaries
from toggl_invoice_generator.config import Settings
from toggl_invoice_generator.toggl import TogglClient
from toggl_invoice_generator.analyze import summarize_time_entries
from datetime import datetime

def main():
    date_str = datetime.now().strftime("%Y%m%d")
    settings = Settings()

    client = TogglClient()
    
    # Use configured date range if specified, otherwise use default (all available data)
    time_entries = client.get_time_entries(
        start_date=settings.start_date,
        end_date=settings.end_date
    )
    
    # Get project summaries (only projects with rate mappings)
    summaries = summarize_time_entries(time_entries, settings.projects)
    for summary in summaries:
        print(summary.short_summary)
    
    # Create and save the invoice using summaries
    invoice_file = create_invoice_from_summaries(summaries, f"invoices/invoice_{date_str}.pdf")
    print(f"Invoice generated successfully: {invoice_file}")

    # Download report with same date range
    client.download_report(
        settings.workspace_id, 
        start_date=settings.start_date,
        end_date=settings.end_date,
        project_ids=[project.project_id for project in settings.projects], 
        filename=f"reports/toggl_report_{date_str}.pdf"
    )
    print(f"Report downloaded successfully: toggl_report_{date_str}.pdf")

if __name__ == "__main__":
    main()