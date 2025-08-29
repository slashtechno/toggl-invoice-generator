from datetime import datetime, timedelta
from typing import List, Optional
from pydantic import BaseModel, computed_field
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from toggl_invoice_generator.toggl import TimeEntry
from toggl_invoice_generator.config import Settings
from toggl_invoice_generator.analyze import ProjectSummary


class InvoiceLineItem(BaseModel):
    """Represents a single line item in an invoice"""
    project_name: str
    hours: float
    hourly_rate: float
    
    @computed_field
    @property
    def amount(self) -> float:
        """Calculate the total amount for this line item"""
        return round(self.hours * self.hourly_rate, 2)


class InvoiceGenerator(BaseModel):
    """Generates PDF invoices from Toggl time entries"""
    settings: Settings = Settings()
    
    def _get_project_rate(self, project_id: int, project_name: str) -> float:
        """Get the hourly rate for a project"""
        for project in self.settings.projects:
            if (project.project_id and project.project_id == project_id) or \
               (project.name and project.name == project_name):
                return project.hourly_rate
        return 0.0
    
    def _group_entries_by_project(self, time_entries: List[TimeEntry]) -> List[InvoiceLineItem]:
        """Group time entries by project and calculate totals"""
        project_totals = {}
        
        for entry in time_entries:
            project_key = (entry.project_id, entry.project_name)
            if project_key not in project_totals:
                project_totals[project_key] = {
                    'hours': 0.0,
                    'rate': self._get_project_rate(entry.project_id, entry.project_name)
                }
            project_totals[project_key]['hours'] += entry.hours
        
        return [
            InvoiceLineItem(
                project_name=project_name,
                hours=totals['hours'],
                hourly_rate=totals['rate']
            )
            for (_, project_name), totals in project_totals.items()
        ]
    
    def generate_pdf_invoice(self, time_entries: List[TimeEntry], filename: str) -> str:
        """Generate a PDF invoice and save it to the specified filename"""
        line_items = self._group_entries_by_project(time_entries)
        total = sum(item.amount for item in line_items)
        
        # Create PDF document
        doc = SimpleDocTemplate(filename, pagesize=letter)
        story = []
        styles = getSampleStyleSheet()
        
        # Title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            spaceAfter=30,
            alignment=1  # Center alignment
        )
        story.append(Paragraph("INVOICE", title_style))
        story.append(Spacer(1, 20))
        
        # Invoice ID
        invoice_id_style = ParagraphStyle(
            'InvoiceID',
            parent=styles['Normal'],
            fontSize=14,
            spaceAfter=20,
            alignment=1  # Center alignment
        )
        story.append(Paragraph(f"Invoice #: {self.settings.invoice_id}", invoice_id_style))
        story.append(Spacer(1, 20))
        
        # Invoice details
        invoice_date = datetime.now()
        due_date = invoice_date + timedelta(weeks=2)
        
        details_data = [
            ['Invoice Date:', invoice_date.strftime("%B %d, %Y")],
            ['Due Date:', due_date.strftime("%B %d, %Y")],
            ['Payment Terms:', self.settings.payment_terms]
        ]
        
        # Add service period if dates are configured
        if self.settings.start_date and self.settings.end_date:
            # Convert YYYY-MM-DD to MM-DD-YYYY format
            start_date_obj = datetime.strptime(self.settings.start_date, "%Y-%m-%d")
            end_date_obj = datetime.strptime(self.settings.end_date, "%Y-%m-%d")
            start_formatted = start_date_obj.strftime("%m-%d-%Y")
            end_formatted = end_date_obj.strftime("%m-%d-%Y")
            details_data.append(['Service Period:', f"{start_formatted} to {end_formatted}"])
        
        details_table = Table(details_data, colWidths=[2*inch, 4*inch])
        details_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
        ]))
        story.append(details_table)
        story.append(Spacer(1, 20))
        
        # Billing information
        if self.settings.billed_to:
            story.append(Paragraph("Bill To:", styles['Heading2']))
            for line in self.settings.billed_to.split('\n'):
                story.append(Paragraph(line, styles['Normal']))
            story.append(Spacer(1, 15))
        
        if self.settings.pay_to:
            story.append(Paragraph("Pay To:", styles['Heading2']))
            for line in self.settings.pay_to.split('\n'):
                story.append(Paragraph(line, styles['Normal']))
            story.append(Spacer(1, 20))
        
        # Line items table
        table_data = [['Project', 'Hours', 'Rate', 'Amount']]
        for item in line_items:
            table_data.append([
                item.project_name,
                f"{item.hours:.2f}",
                f"${item.hourly_rate:.2f}",
                f"${item.amount:.2f}"
            ])
        
        # Add total row with both hours and amount - TOTAL in first column
        total_hours = sum(item.hours for item in line_items)
        table_data.append(['TOTAL', f"{total_hours:.2f}", '', f"${total:.2f}"])
        
        # Create table with styling
        table = Table(table_data, colWidths=[3*inch, 1.5*inch, 1.5*inch, 1.5*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, -1), (-2, -1), colors.lightgrey),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))
        
        story.append(table)
        
        # Build PDF
        doc.build(story)
        return filename
    
    def generate_pdf_invoice_from_summaries(self, summaries: List[ProjectSummary], filename: str) -> str:
        """Generate a PDF invoice from project summaries"""
        # Convert summaries to line items
        line_items = [
            InvoiceLineItem(
                project_name=summary.project.name or f"Project {summary.project.project_id}",
                hours=summary.hours,
                hourly_rate=summary.project.hourly_rate
            )
            for summary in summaries
            if summary.hours > 0  # Only include projects with actual hours
        ]
        
        total_amount = sum(item.amount for item in line_items)
        total_hours = sum(item.hours for item in line_items)
        
        # Create PDF document
        doc = SimpleDocTemplate(filename, pagesize=letter)
        story = []
        styles = getSampleStyleSheet()
        
        # Title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            spaceAfter=30,
            alignment=1  # Center alignment
        )
        story.append(Paragraph("INVOICE", title_style))
        story.append(Spacer(1, 20))
        
        # Invoice ID
        invoice_id_style = ParagraphStyle(
            'InvoiceID',
            parent=styles['Normal'],
            fontSize=14,
            spaceAfter=20,
            alignment=1  # Center alignment
        )
        story.append(Paragraph(f"Invoice #: {self.settings.invoice_id}", invoice_id_style))
        story.append(Spacer(1, 20))
        
        # Invoice details
        invoice_date = datetime.now()
        due_date = invoice_date + timedelta(weeks=2)
        
        details_data = [
            ['Invoice Date:', invoice_date.strftime("%B %d, %Y")],
            ['Due Date:', due_date.strftime("%B %d, %Y")],
            ['Payment Terms:', self.settings.payment_terms]
        ]
        
        # Add service period if dates are configured
        if self.settings.start_date and self.settings.end_date:
            # Convert YYYY-MM-DD to MM-DD-YYYY format
            start_date_obj = datetime.strptime(self.settings.start_date, "%Y-%m-%d")
            end_date_obj = datetime.strptime(self.settings.end_date, "%Y-%m-%d")
            start_formatted = start_date_obj.strftime("%m-%d-%Y")
            end_formatted = end_date_obj.strftime("%m-%d-%Y")
            details_data.append(['Service Period:', f"{start_formatted} to {end_formatted}"])
        
        details_table = Table(details_data, colWidths=[2*inch, 4*inch])
        details_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
        ]))
        story.append(details_table)
        story.append(Spacer(1, 20))
        
        # Billing information
        if self.settings.billed_to:
            story.append(Paragraph("Bill To:", styles['Heading2']))
            for line in self.settings.billed_to.split('\n'):
                story.append(Paragraph(line, styles['Normal']))
            story.append(Spacer(1, 15))
        
        if self.settings.pay_to:
            story.append(Paragraph("Pay To:", styles['Heading2']))
            for line in self.settings.pay_to.split('\n'):
                story.append(Paragraph(line, styles['Normal']))
            story.append(Spacer(1, 20))
        
        # Line items table
        table_data = [['Project', 'Hours', 'Rate', 'Amount']]
        for item in line_items:
            table_data.append([
                item.project_name,
                f"{item.hours:.2f}",
                f"${item.hourly_rate:.2f}",
                f"${item.amount:.2f}"
            ])
        
        # Add total row with both hours and amount - TOTAL in first column
        table_data.append(['TOTAL', f"{total_hours:.2f}", '', f"${total_amount:.2f}"])
        
        # Create table with styling
        table = Table(table_data, colWidths=[3*inch, 1.5*inch, 1.5*inch, 1.5*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, -1), (-2, -1), colors.lightgrey),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))
        
        story.append(table)
        
        # Build PDF
        doc.build(story)
        return filename


def create_invoice(
    time_entries: List[TimeEntry],
    filename: str,
    billed_to: Optional[str] = None,
    pay_to: Optional[str] = None,
    payment_terms: Optional[str] = None,
    invoice_id: Optional[int] = None
) -> str:
    """
    Convenience function to create a PDF invoice from time entries
    
    Args:
        time_entries: List of Toggl time entries
        filename: Output PDF filename
        billed_to: Override billing address from config
        pay_to: Override payment address from config
        payment_terms: Override payment terms from config
        invoice_id: Override invoice ID from config
    
    Returns:
        Filename of the generated PDF
    """
    # Create temporary settings override if custom values provided
    if any([billed_to, pay_to, payment_terms, invoice_id]):
        settings = Settings()
        if billed_to is not None:
            settings.billed_to = billed_to
        if pay_to is not None:
            settings.pay_to = pay_to
        if payment_terms is not None:
            settings.payment_terms = payment_terms
        if invoice_id is not None:
            settings.invoice_id = invoice_id
        generator = InvoiceGenerator(settings=settings)
    else:
        generator = InvoiceGenerator()
    
    return generator.generate_pdf_invoice(time_entries, filename)


def create_invoice_from_summaries(
    summaries: List[ProjectSummary],
    filename: str,
    billed_to: Optional[str] = None,
    pay_to: Optional[str] = None,
    payment_terms: Optional[str] = None,
    invoice_id: Optional[int] = None
) -> str:
    """
    Convenience function to create a PDF invoice from project summaries
    
    Args:
        summaries: List of project summaries (only projects with rate mappings)
        filename: Output PDF filename
        billed_to: Override billing address from config
        pay_to: Override payment address from config
        payment_terms: Override payment terms from config
        invoice_id: Override invoice ID from config
    
    Returns:
        Filename of the generated PDF
    """
    # Create temporary settings override if custom values provided
    if any([billed_to, pay_to, payment_terms, invoice_id]):
        settings = Settings()
        if billed_to is not None:
            settings.billed_to = billed_to
        if pay_to is not None:
            settings.pay_to = pay_to
        if payment_terms is not None:
            settings.payment_terms = payment_terms
        if invoice_id is not None:
            settings.invoice_id = invoice_id
        generator = InvoiceGenerator(settings=settings)
    else:
        generator = InvoiceGenerator()
    
    return generator.generate_pdf_invoice_from_summaries(summaries, filename)

