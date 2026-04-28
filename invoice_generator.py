"""
Professional Invoice Generator for Brand Cartel
Generates beautiful PDF invoices with Azure blue theme
SARS-compliant tax invoices for South African businesses
"""

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER
from reportlab.pdfgen import canvas
from datetime import datetime
import os

# Azure Blue Color Theme
AZURE_BLUE = colors.HexColor('#0078D4')
LIGHT_AZURE = colors.HexColor('#E6F2FF')
DARK_GRAY = colors.HexColor('#333333')
MEDIUM_GRAY = colors.HexColor('#666666')
LIGHT_GRAY = colors.HexColor('#F5F5F5')

class InvoiceGenerator:
    """Generate professional SARS-compliant invoices"""
    
    def __init__(self, order, business_info=None):
        """
        Initialize invoice generator
        
        Args:
            order: Order object with all order details
            business_info: Dictionary with business information
        """
        self.order = order
        self.business_info = business_info or self._get_default_business_info()
        
    def _get_default_business_info(self):
        """Get default business information"""
        return {
            'name': 'Brand Cartel Online Store',
            'vat_number': '4123456789',
            'registration': '2023/123456/07',
            'address': 'Unit 5, Business Park\nCape Town, 8001\nSouth Africa',
            'phone': '+27 21 123 4567',
            'email': 'accounts@brandcartel.co.za',
            'website': 'www.brandcartel.co.za'
        }
    
    def generate_invoice(self, filename):
        """
        Generate PDF invoice
        
        Args:
            filename: Full path where to save the PDF
            
        Returns:
            str: Path to generated invoice
        """
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        
        # Create PDF document
        doc = SimpleDocTemplate(
            filename,
            pagesize=A4,
            rightMargin=2*cm,
            leftMargin=2*cm,
            topMargin=2*cm,
            bottomMargin=2*cm
        )
        
        # Container for PDF elements
        elements = []
        
        # Add header
        elements.extend(self._create_header())
        
        # Add spacing
        elements.append(Spacer(1, 0.5*cm))
        
        # Add invoice details
        elements.extend(self._create_invoice_details())
        
        # Add spacing
        elements.append(Spacer(1, 0.5*cm))
        
        # Add customer details
        elements.extend(self._create_customer_details())
        
        # Add spacing
        elements.append(Spacer(1, 0.8*cm))
        
        # Add items table
        elements.extend(self._create_items_table())
        
        # Add spacing
        elements.append(Spacer(1, 0.5*cm))
        
        # Add totals
        elements.extend(self._create_totals())
        
        # Add spacing
        elements.append(Spacer(1, 1*cm))
        
        # Add payment info
        elements.extend(self._create_payment_info())
        
        # Add spacing
        elements.append(Spacer(1, 0.5*cm))
        
        # Add footer
        elements.extend(self._create_footer())
        
        # Build PDF
        doc.build(elements)
        
        return filename
    
    def _create_header(self):
        """Create invoice header with business info"""
        elements = []
        styles = getSampleStyleSheet()
        
        # Company name style
        company_style = ParagraphStyle(
            'CompanyName',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=AZURE_BLUE,
            spaceAfter=0.1*cm,
            alignment=TA_LEFT
        )
        
        # Create header table (2 columns: business info and invoice title)
        header_data = []
        
        # Left column - Business Info
        left_col = [
            Paragraph(f"<b>{self.business_info['name']}</b>", company_style),
            Paragraph(self.business_info['address'].replace('\n', '<br/>'), 
                     ParagraphStyle('Address', fontSize=9, textColor=MEDIUM_GRAY)),
            Paragraph(f"Tel: {self.business_info['phone']}", 
                     ParagraphStyle('Contact', fontSize=9, textColor=MEDIUM_GRAY)),
            Paragraph(f"Email: {self.business_info['email']}", 
                     ParagraphStyle('Contact', fontSize=9, textColor=MEDIUM_GRAY)),
        ]
        
        # Right column - Invoice title
        invoice_style = ParagraphStyle(
            'InvoiceTitle',
            parent=styles['Heading1'],
            fontSize=28,
            textColor=AZURE_BLUE,
            alignment=TA_RIGHT
        )
        
        tax_invoice_style = ParagraphStyle(
            'TaxInvoice',
            fontSize=10,
            textColor=MEDIUM_GRAY,
            alignment=TA_RIGHT
        )
        
        right_col = [
            Paragraph("<b>TAX INVOICE</b>", invoice_style),
            Paragraph("<br/>SARS Compliant", tax_invoice_style),
        ]
        
        # Create table
        header_table = Table(
            [[left_col, right_col]],
            colWidths=[10*cm, 7*cm]
        )
        
        header_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        
        elements.append(header_table)
        
        # Add separator line
        line_table = Table([['']], colWidths=[17*cm])
        line_table.setStyle(TableStyle([
            ('LINEABOVE', (0, 0), (-1, -1), 2, AZURE_BLUE),
            ('TOPPADDING', (0, 0), (-1, -1), 0.3*cm),
        ]))
        elements.append(line_table)
        
        return elements
    
    def _create_invoice_details(self):
        """Create invoice number and date section"""
        elements = []
        
        # Create details table
        details_data = [
            ['Invoice Number:', f'<b>{self.order.order_number}</b>'],
            ['Invoice Date:', f'<b>{self.order.created_at.strftime("%d %B %Y")}</b>'],
            ['Status:', f'<b>{self.order.status.upper()}</b>'],
        ]
        
        details_table = Table(details_data, colWidths=[4*cm, 6*cm])
        details_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica'),
            ('FONTNAME', (1, 0), (1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('TEXTCOLOR', (0, 0), (0, -1), MEDIUM_GRAY),
            ('TEXTCOLOR', (1, 0), (1, -1), DARK_GRAY),
            ('TOPPADDING', (0, 0), (-1, -1), 0.1*cm),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0.1*cm),
        ]))
        
        elements.append(details_table)
        
        return elements
    
    def _create_customer_details(self):
        """Create customer billing and shipping information"""
        elements = []
        
        # Section title
        title_style = ParagraphStyle(
            'SectionTitle',
            fontSize=12,
            textColor=AZURE_BLUE,
            fontName='Helvetica-Bold',
            spaceAfter=0.3*cm
        )
        
        elements.append(Paragraph('BILL TO', title_style))
        
        # Customer info
        customer = self.order.user
        address_lines = self.order.shipping_address.split('\n')
        
        customer_data = [
            [f'<b>{customer.username}</b>'],
            [customer.email],
            [address_lines[0]] if len(address_lines) > 0 else [''],
        ]
        
        # Add remaining address lines
        for line in address_lines[1:]:
            customer_data.append([line])
        
        customer_table = Table(customer_data, colWidths=[17*cm])
        customer_table.setStyle(TableStyle([
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('TEXTCOLOR', (0, 0), (-1, -1), DARK_GRAY),
            ('TOPPADDING', (0, 0), (-1, -1), 0.05*cm),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0.05*cm),
        ]))
        
        elements.append(customer_table)
        
        return elements
    
    def _create_items_table(self):
        """Create table of ordered items"""
        elements = []
        
        # Table header
        header_style = ParagraphStyle(
            'TableHeader',
            fontSize=10,
            textColor=colors.white,
            fontName='Helvetica-Bold',
            alignment=TA_LEFT
        )
        
        header_data = [
            Paragraph('DESCRIPTION', header_style),
            Paragraph('QUANTITY', header_style),
            Paragraph('UNIT PRICE', header_style),
            Paragraph('TOTAL', header_style),
        ]
        
        # Start with header
        items_data = [header_data]
        
        # Add order items
        for item in self.order.items:
            items_data.append([
                item.product.name,
                str(item.quantity),
                f'R {item.price:,.2f}',
                f'R {(item.quantity * item.price):,.2f}'
            ])
        
        # Calculate delivery
        subtotal = sum(item.quantity * item.price for item in self.order.items)
        delivery_charge = 0 if subtotal >= 500 else 60
        
        # Add delivery row if applicable
        if delivery_charge > 0:
            items_data.append([
                'Delivery Charge',
                '1',
                f'R {delivery_charge:,.2f}',
                f'R {delivery_charge:,.2f}'
            ])
        
        # Create table
        items_table = Table(
            items_data,
            colWidths=[9*cm, 2.5*cm, 2.5*cm, 3*cm]
        )
        
        # Style the table
        items_table.setStyle(TableStyle([
            # Header row
            ('BACKGROUND', (0, 0), (-1, 0), AZURE_BLUE),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('TOPPADDING', (0, 0), (-1, 0), 0.3*cm),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 0.3*cm),
            
            # Data rows
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('TOPPADDING', (0, 1), (-1, -1), 0.2*cm),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 0.2*cm),
            ('TEXTCOLOR', (0, 1), (-1, -1), DARK_GRAY),
            
            # Alignment
            ('ALIGN', (1, 0), (1, -1), 'CENTER'),
            ('ALIGN', (2, 0), (-1, -1), 'RIGHT'),
            
            # Grid
            ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
            
            # Alternating row colors
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, LIGHT_GRAY]),
        ]))
        
        elements.append(items_table)
        
        return elements
    
    def _create_totals(self):
        """Create totals section with VAT breakdown"""
        elements = []
        
        # Calculate amounts
        subtotal = sum(item.quantity * item.price for item in self.order.items)
        delivery_charge = 0 if subtotal >= 500 else 60
        total_incl_vat = self.order.total_amount
        
        # Calculate VAT (15% included in price)
        total_excl_vat = total_incl_vat / 1.15
        vat_amount = total_incl_vat - total_excl_vat
        
        # Create totals data
        totals_data = [
            ['Subtotal (Excl. VAT):', f'R {total_excl_vat:,.2f}'],
            ['VAT (15%):', f'R {vat_amount:,.2f}'],
            ['', ''],  # Spacer
            ['<b>TOTAL DUE:</b>', f'<b>R {total_incl_vat:,.2f}</b>'],
        ]
        
        # Create table (right-aligned)
        totals_table = Table(totals_data, colWidths=[7*cm, 3*cm])
        totals_table.setStyle(TableStyle([
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
            ('TEXTCOLOR', (0, 0), (-1, 2), MEDIUM_GRAY),
            ('TOPPADDING', (0, 0), (-1, -1), 0.1*cm),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0.1*cm),
            
            # Total row styling
            ('FONTSIZE', (0, 3), (-1, 3), 14),
            ('TEXTCOLOR', (0, 3), (-1, 3), AZURE_BLUE),
            ('LINEABOVE', (0, 3), (-1, 3), 2, AZURE_BLUE),
            ('TOPPADDING', (0, 3), (-1, 3), 0.3*cm),
        ]))
        
        # Wrapper table to position on right
        wrapper = Table([[totals_table]], colWidths=[17*cm])
        wrapper.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
        ]))
        
        elements.append(wrapper)
        
        return elements
    
    def _create_payment_info(self):
        """Create payment information section"""
        elements = []
        
        # Title
        title_style = ParagraphStyle(
            'PaymentTitle',
            fontSize=11,
            textColor=AZURE_BLUE,
            fontName='Helvetica-Bold',
            spaceAfter=0.2*cm
        )
        
        elements.append(Paragraph('PAYMENT INFORMATION', title_style))
        
        # Payment details
        payment_text = f"""
        <font size=9 color={MEDIUM_GRAY}>
        Payment Method: <b>{self.order.payment_method or 'Not specified'}</b><br/>
        Payment Status: <b>{self.order.status.upper()}</b><br/>
        <br/>
        Please retain this invoice for your records.
        </font>
        """
        
        elements.append(Paragraph(payment_text, ParagraphStyle('Payment', fontSize=9)))
        
        return elements
    
    def _create_footer(self):
        """Create invoice footer with tax compliance info"""
        elements = []
        
        # SARS compliance notice
        footer_style = ParagraphStyle(
            'Footer',
            fontSize=8,
            textColor=MEDIUM_GRAY,
            alignment=TA_CENTER,
            leading=10
        )
        
        footer_text = f"""
        <b>TAX INVOICE - SARS COMPLIANT</b><br/>
        VAT Registration Number: {self.business_info['vat_number']} | 
        Company Registration: {self.business_info['registration']}<br/>
        {self.business_info['website']} | {self.business_info['email']}<br/>
        <br/>
        This is a computer-generated invoice and does not require a signature.
        """
        
        elements.append(Spacer(1, 0.5*cm))
        
        # Add separator line
        line_table = Table([['']], colWidths=[17*cm])
        line_table.setStyle(TableStyle([
            ('LINEABOVE', (0, 0), (-1, -1), 1, LIGHT_GRAY),
        ]))
        elements.append(line_table)
        
        elements.append(Spacer(1, 0.3*cm))
        elements.append(Paragraph(footer_text, footer_style))
        
        return elements


def generate_order_invoice(order, business_info=None):
    """
    Convenience function to generate invoice for an order
    
    Args:
        order: Order object
        business_info: Optional business information dictionary
        
    Returns:
        str: Path to generated invoice PDF
    """
    # Create invoices directory
    invoice_dir = os.path.join('static', 'invoices')
    os.makedirs(invoice_dir, exist_ok=True)
    
    # Generate filename
    filename = os.path.join(
        invoice_dir,
        f'invoice_{order.order_number}_{datetime.now().strftime("%Y%m%d")}.pdf'
    )
    
    # Generate invoice
    generator = InvoiceGenerator(order, business_info)
    return generator.generate_invoice(filename)
