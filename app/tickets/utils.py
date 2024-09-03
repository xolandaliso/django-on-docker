from datetime import timedelta
from urllib import request
from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from .models import Employee, Ticket, Type, TicketComments, CustomUser, RecurringTicket
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.utils.html import strip_tags
import logging

logger = logging.getLogger(__name__)

@shared_task
def send_email_task(recipient_email, subject, html_message):
    email_from = settings.DEFAULT_FROM_EMAIL
    from_name = settings.EMAIL_FROM_NAME  # generic name to use in the email
    email = EmailMessage(
        subject,
        html_message,
        f'{from_name} <{email_from}>',
        [recipient_email]
    )
    email.content_subtype = "html"  # set the content type to HTML
    email.send()

@shared_task
def check_high_priority_tickets():
    now = timezone.now()
    ten_minutes_ago = now - timedelta(minutes=10)

    # Get all 'High priority - P0' types
    high_priority_types = Type.objects.filter(type_description__iexact='High priority - P0')

    if not high_priority_types.exists():
        logger.error("'High priority' type does not exist in the Type model")
        return "No 'High priority' type found"

    # Use __in to match any of the high priority types
    high_priority_tickets = Ticket.objects.filter(
        ticket_type__in=high_priority_types,
        ticket_status__status_description='open',
        created_at__lte=ten_minutes_ago
    )
    
    logger.info(f"Found {high_priority_tickets.count()} high priority tickets open for over 10 minutes")
    
    for ticket in high_priority_tickets:
        department = ticket.employee.department
        managers = Employee.objects.filter(department=department, role='manager')
        
        for manager in managers:
            context = {
                'ticket_id': ticket.id,
                'ticket_type': ticket.ticket_type.type_description,
                'ticket_description': ticket.ticket_description,
                'department_name': department.department_name,
                'current_time': now.strftime('%Y-%m-%d %H:%M:%S')
            }
            
            email_content = render_to_string('emails/high_priority_alert.html', context)
            
            try:
                send_email_task.delay(
                    manager.employee.email,
                    f'Alert: High Priority Ticket Open for Over 10 Minutes',
                    email_content
                )
                logger.info(f"Sent alert email for ticket {ticket.id} to manager {manager.employee.email}")
            except Exception as e:
                logger.error(f"Failed to send alert email for ticket {ticket.id} to manager {manager.employee.email}: {str(e)}")

    return f"Processed {high_priority_tickets.count()} high priority tickets"

@shared_task
def send_comment_notification(context):
    # retrieve necessary objects using IDs
    comment = TicketComments.objects.get(id=context['comment_id'])
    ticket = Ticket.objects.get(id=context['ticket_id'])
    user = CustomUser.objects.get(id=context['user_id'])
    request_user = ticket.request_user
    
    # determine the recipient

    recipient_email = None
    if request_user == comment.user:
        # email the employee assigned to the ticket
        recipient_email = ticket.employee.employee.email
    else:
        # email the user who created the comment
        recipient_email = request_user.email
    
    # prepare context for email
    email_context = {
        'user': user,
        'comment': comment,
    }

    # render email content from the template
    email_content = render_to_string(
        'emails/comment_notification.html',
        email_context
    )

    # send email using the predefined Celery task
    send_email_task.delay(
        recipient_email,
        'New Comment on Your Ticket',
        email_content
    )

@shared_task
def send_recurring_ticket_email():
    recurring_tickets = RecurringTicket.objects.filter(next_run__lte=timezone.now())
    for recurring_ticket in recurring_tickets:
        subject = f"Reminder: Recurring Ticket - {recurring_ticket.recurring_description[:50]}..."
        
        employee_department = recurring_ticket.employee.department
        requester_department = recurring_ticket.get_requester_department()

        html_message = render_to_string('emails/recurring_ticket_reminder.html', {
            'recurring_description': recurring_ticket.recurring_description,
            'employee_name': recurring_ticket.employee.employee.get_full_name(),
            'employee_username': recurring_ticket.employee.employee.username,
            'frequency': recurring_ticket.get_frequency_display(),
            'employee_department': employee_department.department_name if employee_department else 'N/A',
            #'requester_name': recurring_ticket.requester.get_full_name(),
            #'requester_username': recurring_ticket.requester.username,
            'requester_department': requester_department.department_name if requester_department else 'N/A',
            'next_run': recurring_ticket.next_run,
        })
        
        send_email_task.delay(
            recipient_email=recurring_ticket.employee.employee.email,
            subject=subject,
            html_message=html_message
        )
        
        recurring_ticket.next_run = recurring_ticket.calculate_next_run()
        recurring_ticket.save()

    return f"Processed {recurring_tickets.count()} recurring tickets."