from asyncio.log import logger
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from .models import Ticket, TicketComments, CustomUser
from .utils import send_email_task, send_comment_notification
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from datetime import datetime
import logging
from django.urls import reverse

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Ticket)
def send_ticket_creation_notifications(sender, instance, created, **kwargs):
    if created:
        ticket = instance
        selected_employee = ticket.employee
        request_user = ticket.request_user
        department = selected_employee.department
        request_user_department = request_user.get_department()


        site_url = settings.SITE_URL  # Ensure SITE_URL is set in your settings
        status_url = f"{site_url}/ticket-status/{instance.id}/"
        # email


        # context for HTML templates
        context_employee = {
            'employee_name': selected_employee.employee.get_full_name(),
            'ticket_type': ticket.ticket_type if ticket.ticket_type else 'N/A',
            'ticket_description': ticket.ticket_description,
            'location': ticket.location if ticket.location else 'N/A',
            'department_name': department.department_name,
            'request_user_department': request_user_department.department_name if request_user_department else 'N/A',
            'current_year': datetime.now().year,
            'status_url': status_url,  # Add URL to context
        }

        context_user = {
            'employee_name': selected_employee.employee.get_full_name(),
            'user_name': request_user.get_full_name(),
            'ticket_type': ticket.ticket_type if ticket.ticket_type else 'N/A',
            'ticket_description': ticket.ticket_description,
            'department_name': department.department_name,
            'current_year': datetime.now().year,
        }

        # render email content from templates and strip HTML tags for plain text
        employee_email_content = render_to_string(
            'emails/ticket_assigned.html', 
            context_employee
        )
        
        user_email_content = render_to_string(
                'emails/ticket_created.html', 
                context_user
        )
    
        # send email notification to the employee
        send_email_task.delay(
            selected_employee.employee.email,
            f'New {context_employee["ticket_type"]} Ticket Assigned to You',
            employee_email_content
        )

        # send email notification to the user
        send_email_task.delay(
            request_user.email,
            'Ticket Created Successfully',
            user_email_content
        )


@receiver(pre_save, sender=Ticket)
def check_status_change(sender, instance, **kwargs):
    if instance.pk:
        old_ticket = Ticket.objects.get(pk=instance.pk)
        instance._old_status = old_ticket.ticket_status

@receiver(post_save, sender=Ticket)
def send_ticket_status_update_email(sender, instance, **kwargs):
    # check if the ticket status was changed
    if hasattr(instance, '_old_status'):
        old_status = instance._old_status
        new_status = instance.ticket_status

        if old_status != new_status:
            if new_status.status_description == 'closed':
                logger.info(f"Ticket {instance.id} status updated to closed. Preparing email notifications.")
                
                site_url = settings.SITE_URL  # Ensure SITE_URL is set in your settings
                reopen_ticket_url = f"{site_url}/reopen-ticket/{instance.id}/"
                rating_url = f"{site_url}/rate-service/{instance.id}/"
                # email
                context = {
                    'user_name': instance.request_user.get_full_name(),
                    'ticket_id': instance.id,
                    'ticket_type': instance.ticket_type,
                    'ticket_description': instance.ticket_description,
                    'ticket_status': new_status.status_description,
                    'ticket_resolution': instance.ticket_resolution,
                    'department_name': instance.employee.department.department_name,
                    'reopen_ticket_url': reopen_ticket_url,
                    'rating_url': rating_url 
                }
                # context for HTML templates
                email_content = render_to_string(
                    'emails/ticket_closed.html', 
                    context
                )
                

                # alert user who created the ticket
                send_email_task.delay(
                    instance.request_user.email,
                    f'Ticket {instance.id} Closed',
                    email_content
                )

@receiver(post_save, sender=TicketComments)
def handle_comment_saved(sender, instance, **kwargs):
    comment = instance
    ticket = comment.ticket

    # Serialize necessary data
    context = {
        'comment_id': comment.id,
        'ticket_id': ticket.id,
        'user_id': comment.user.id,
    }

    # Trigger the Celery task
    send_comment_notification.delay(context)
