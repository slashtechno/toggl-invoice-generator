#!/usr/bin/env python3
"""
Script to generate an invoice with mock data using the toggl-invoice-generator package.
This bypasses the need for a config.toml file by directly providing mock data.
"""

from datetime import datetime, timedelta
from toggl_invoice_generator.invoice import create_invoice_from_summaries
from toggl_invoice_generator.analyze import ProjectSummary
from toggl_invoice_generator.config import Project
from toggl_invoice_generator.toggl import TimeEntry

def main():
    # Create mock projects with simple names
    mock_projects = [
        Project(
            project_id=123456,
            name="Project 1",
            hourly_rate=75.00
        ),
        Project(
            project_id=789012,
            name="Project 2",
            hourly_rate=85.00
        ),
        Project(
            project_id=345678,
            name="Project 3",
            hourly_rate=95.00
        )
    ]
    
    # Create mock time entries for each project
    base_date = datetime.now() - timedelta(days=30)
    mock_time_entries = []
    
    # Project 1: 24.5 hours
    for i in range(10):
        start_time = base_date + timedelta(days=i*3, hours=9)
        mock_time_entries.append(TimeEntry(
            client_name="Mock Client Inc.",
            duration=int(2.45 * 3600),  # 2.45 hours in seconds
            project_name="Project 1",
            project_id=123456,
            start=start_time,
            stop=start_time + timedelta(hours=2, minutes=27)
        ))
    
    # Project 2: 18.0 hours
    for i in range(9):
        start_time = base_date + timedelta(days=i*3 + 1, hours=14)
        mock_time_entries.append(TimeEntry(
            client_name="Mock Client Inc.",
            duration=int(2.0 * 3600),  # 2.0 hours in seconds
            project_name="Project 2",
            project_id=789012,
            start=start_time,
            stop=start_time + timedelta(hours=2)
        ))
    
    # Project 3: 12.5 hours
    for i in range(5):
        start_time = base_date + timedelta(days=i*6, hours=10)
        mock_time_entries.append(TimeEntry(
            client_name="Mock Client Inc.",
            duration=int(2.5 * 3600),  # 2.5 hours in seconds
            project_name="Project 3",
            project_id=345678,
            start=start_time,
            stop=start_time + timedelta(hours=2, minutes=30)
        ))
    
    # Create project summaries
    mock_summaries = []
    for project in mock_projects:
        project_entries = [entry for entry in mock_time_entries if entry.project_id == project.project_id]
        total_hours = sum(entry.hours for entry in project_entries)
        mock_summaries.append(ProjectSummary(
            project=project,
            hours=total_hours,
            entries=project_entries
        ))
    
    # Generate timestamp for filename
    date_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    invoice_filename = f"invoices/mock_invoice_{date_str}.pdf"
    
    # Invoice details
    billed_to = "Mock Client Inc.\n123 Fake Street\nTest City, TC 12345"
    pay_to = "Mock Developer\n456 Developer Lane\nCode City, CC 67890"
    payment_terms = "Net 30"
    invoice_id = 1001
    
    # Create and save the invoice
    print("Generating mock invoice...")
    print(f"Projects included:")
    for summary in mock_summaries:
        print(f"  - {summary.short_summary}")
    
    try:
        invoice_file = create_invoice_from_summaries(
            mock_summaries, 
            invoice_filename,
            billed_to=billed_to,
            pay_to=pay_to,
            payment_terms=payment_terms,
            invoice_id=invoice_id
        )
        print(f"\n✅ Invoice generated successfully: {invoice_file}")
        print(f"📄 Total invoice amount: ${sum(s.total_revenue for s in mock_summaries):,.2f}")
        print(f"📋 Invoice ID: {invoice_id}")
        print(f"💰 Payment Terms: {payment_terms}")
    except Exception as e:
        print(f"❌ Error generating invoice: {e}")

if __name__ == "__main__":
    main()
