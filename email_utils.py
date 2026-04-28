"""
Email Utility for Brand Cartel
Sends professional emails with invoice attachments
"""

from flask_mail import Mail, Message
from flask import current_app
import os

mail = Mail()

def init_mail(app):
    """Initialize Flask-Mail with app configuration"""
    # Email configuration
    app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT', 587))
    app.config['MAIL_USE_TLS'] = os.environ.get('MAIL_USE_TLS', 'True') == 'True'
    app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME')
    app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')
    app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_DEFAULT_SENDER', 'noreply@brandcartel.co.za')
    
    mail.init_app(app)
    return mail


def send_invoice_email(customer_email, customer_name, order, invoice_path):
    """
    Send invoice email to customer
    
    Args:
        customer_email: Customer's email address
        customer_name: Customer's name
        order: Order object
        invoice_path: Path to the invoice PDF file
        
    Returns:
        bool: True if email sent successfully, False otherwise
    """
    try:
        # Create email message
        msg = Message(
            subject=f'Invoice #{order.order_number} - Brand Cartel',
            recipients=[customer_email],
            sender=current_app.config['MAIL_DEFAULT_SENDER']
        )
        
        # Email body (HTML)
        msg.html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 20px;
                }}
                .header {{
                    background: linear-gradient(135deg, #0078D4 0%, #005a9e 100%);
                    color: white;
                    padding: 30px 20px;
                    text-align: center;
                    border-radius: 8px 8px 0 0;
                }}
                .header h1 {{
                    margin: 0;
                    font-size: 28px;
                    font-weight: 300;
                }}
                .content {{
                    background: #ffffff;
                    padding: 30px;
                    border: 1px solid #e0e0e0;
                    border-top: none;
                }}
                .invoice-details {{
                    background: #f8f9fa;
                    padding: 20px;
                    border-radius: 6px;
                    margin: 20px 0;
                    border-left: 4px solid #0078D4;
                }}
                .invoice-details table {{
                    width: 100%;
                    border-collapse: collapse;
                }}
                .invoice-details td {{
                    padding: 8px 0;
                    border-bottom: 1px solid #e0e0e0;
                }}
                .invoice-details td:first-child {{
                    color: #666;
                    width: 40%;
                }}
                .invoice-details td:last-child {{
                    font-weight: 600;
                    color: #0078D4;
                }}
                .total {{
                    font-size: 24px;
                    color: #0078D4;
                    font-weight: bold;
                }}
                .button {{
                    display: inline-block;
                    padding: 12px 30px;
                    background: #0078D4;
                    color: white;
                    text-decoration: none;
                    border-radius: 4px;
                    margin: 20px 0;
                    font-weight: 500;
                }}
                .button:hover {{
                    background: #005a9e;
                }}
                .footer {{
                    text-align: center;
                    padding: 20px;
                    color: #666;
                    font-size: 12px;
                    border-top: 1px solid #e0e0e0;
                    margin-top: 30px;
                }}
                .attachment-notice {{
                    background: #e6f2ff;
                    border: 1px solid #0078D4;
                    padding: 15px;
                    border-radius: 6px;
                    margin: 20px 0;
                    text-align: center;
                }}
                .attachment-notice strong {{
                    color: #0078D4;
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>Thank You for Your Order!</h1>
                <p style="margin: 10px 0 0 0; font-size: 16px; opacity: 0.95;">
                    Your order has been confirmed
                </p>
            </div>
            
            <div class="content">
                <p>Dear <strong>{customer_name}</strong>,</p>
                
                <p>Thank you for shopping with Brand Cartel! Your order has been successfully placed and is being processed.</p>
                
                <div class="invoice-details">
                    <table>
                        <tr>
                            <td>Invoice Number:</td>
                            <td>#{order.order_number}</td>
                        </tr>
                        <tr>
                            <td>Order Date:</td>
                            <td>{order.created_at.strftime('%d %B %Y')}</td>
                        </tr>
                        <tr>
                            <td>Payment Method:</td>
                            <td>{order.payment_method or 'Not specified'}</td>
                        </tr>
                        <tr>
                            <td>Status:</td>
                            <td>{order.status.upper()}</td>
                        </tr>
                        <tr style="border-top: 2px solid #0078D4;">
                            <td><strong>Total Amount:</strong></td>
                            <td class="total">R {order.total_amount:,.2f}</td>
                        </tr>
                    </table>
                </div>
                
                <div class="attachment-notice">
                    <strong>📎 Tax Invoice Attached</strong><br/>
                    <span style="font-size: 13px; color: #666;">
                        Your SARS-compliant tax invoice is attached to this email as a PDF file.
                    </span>
                </div>
                
                <p><strong>Order Summary:</strong></p>
                <ul>
                    {''.join([f'<li>{item.product.name} - Qty: {item.quantity} - R {(item.quantity * item.price):,.2f}</li>' for item in order.items])}
                </ul>
                
                <p><strong>Delivery Address:</strong></p>
                <p style="background: #f8f9fa; padding: 15px; border-radius: 6px; white-space: pre-line;">
{order.shipping_address}
                </p>
                
                <p>You can track your order status at any time by logging into your account.</p>
                
                <div style="text-align: center;">
                    <a href="{current_app.config.get('BASE_URL', 'http://localhost:5000')}/orders" class="button">
                        View Order Details
                    </a>
                </div>
                
                <p>If you have any questions about your order, please don't hesitate to contact us.</p>
                
                <p style="margin-top: 30px;">
                    Best regards,<br/>
                    <strong style="color: #0078D4;">The Brand Cartel Team</strong>
                </p>
            </div>
            
            <div class="footer">
                <p>
                    <strong>Brand Cartel Online Store</strong><br/>
                    Cape Town, South Africa<br/>
                    Tel: +27 21 123 4567 | Email: support@brandcartel.co.za<br/>
                    <a href="www.brandcartel.co.za" style="color: #0078D4;">www.brandcartel.co.za</a>
                </p>
                <p style="margin-top: 15px; font-size: 11px; color: #999;">
                    This is an automated email. Please do not reply to this email.<br/>
                    VAT Registration: 4123456789 | Company Registration: 2023/123456/07
                </p>
            </div>
        </body>
        </html>
        """
        
        # Plain text version
        msg.body = f"""
Dear {customer_name},

Thank you for shopping with Brand Cartel! Your order has been successfully placed.

Invoice Number: #{order.order_number}
Order Date: {order.created_at.strftime('%d %B %Y')}
Total Amount: R {order.total_amount:,.2f}
Status: {order.status.upper()}

Your SARS-compliant tax invoice is attached to this email.

Delivery Address:
{order.shipping_address}

You can track your order at: {current_app.config.get('BASE_URL', 'http://localhost:5000')}/orders

Best regards,
The Brand Cartel Team

---
Brand Cartel Online Store
Cape Town, South Africa
Tel: +27 21 123 4567
Email: support@brandcartel.co.za
Web: www.brandcartel.co.za

VAT Registration: 4123456789 | Company Registration: 2023/123456/07
        """
        
        # Attach invoice PDF
        if os.path.exists(invoice_path):
            with open(invoice_path, 'rb') as fp:
                msg.attach(
                    filename=f'Invoice_{order.order_number}.pdf',
                    content_type='application/pdf',
                    data=fp.read()
                )
        
        # Send email
        mail.send(msg)
        return True
        
    except Exception as e:
        current_app.logger.error(f'Error sending invoice email: {str(e)}')
        return False


def send_admin_notification(order, invoice_path):
    """
    Send order notification to admin
    
    Args:
        order: Order object
        invoice_path: Path to the invoice PDF file
        
    Returns:
        bool: True if email sent successfully
    """
    try:
        admin_email = current_app.config.get('ADMIN_EMAIL', 'admin@brandcartel.co.za')
        
        msg = Message(
            subject=f'New Order #{order.order_number} - R {order.total_amount:,.2f}',
            recipients=[admin_email],
            sender=current_app.config['MAIL_DEFAULT_SENDER']
        )
        
        msg.html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    line-height: 1.6;
                    color: #333;
                }}
                .header {{
                    background: #0078D4;
                    color: white;
                    padding: 20px;
                    border-radius: 6px;
                }}
                .content {{
                    padding: 20px;
                }}
                table {{
                    width: 100%;
                    border-collapse: collapse;
                    margin: 15px 0;
                }}
                th, td {{
                    padding: 10px;
                    border: 1px solid #ddd;
                    text-align: left;
                }}
                th {{
                    background: #0078D4;
                    color: white;
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <h2>🛍️ New Order Received</h2>
            </div>
            <div class="content">
                <p><strong>Order #{order.order_number}</strong></p>
                
                <table>
                    <tr>
                        <td><strong>Customer:</strong></td>
                        <td>{order.user.username} ({order.user.email})</td>
                    </tr>
                    <tr>
                        <td><strong>Total Amount:</strong></td>
                        <td><strong>R {order.total_amount:,.2f}</strong></td>
                    </tr>
                    <tr>
                        <td><strong>Payment Method:</strong></td>
                        <td>{order.payment_method}</td>
                    </tr>
                    <tr>
                        <td><strong>Status:</strong></td>
                        <td>{order.status.upper()}</td>
                    </tr>
                </table>
                
                <p><strong>Items:</strong></p>
                <ul>
                    {''.join([f'<li>{item.product.name} x {item.quantity} = R {(item.quantity * item.price):,.2f}</li>' for item in order.items])}
                </ul>
                
                <p><strong>Shipping Address:</strong></p>
                <p style="background: #f5f5f5; padding: 10px; border-radius: 4px; white-space: pre-line;">
{order.shipping_address}
                </p>
                
                <p>Invoice attached and recorded in accounting system.</p>
            </div>
        </body>
        </html>
        """
        
        # Attach invoice
        if os.path.exists(invoice_path):
            with open(invoice_path, 'rb') as fp:
                msg.attach(
                    filename=f'Invoice_{order.order_number}.pdf',
                    content_type='application/pdf',
                    data=fp.read()
                )
        
        mail.send(msg)
        return True
        
    except Exception as e:
        current_app.logger.error(f'Error sending admin notification: {str(e)}')
        return False
