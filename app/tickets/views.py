from datetime import timedelta
from django.urls import reverse
from django.utils import timezone
from multiprocessing import context
from collections import defaultdict
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Q, Count
from .utils import send_email_task
from django.core.paginator import Paginator
from django.http import HttpResponseRedirect
from django.template.loader import render_to_string
from django.contrib.auth.forms import UserCreationForm
from .models import Department, Employee, Status, Ticket, Documents, RecurringTicket
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login as auth_login, authenticate, logout
from django.shortcuts import render, redirect, HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from .forms import TicketForm, CustomUserForm, TicketCommentsForm, ServiceRatingForm, RecurringTicketForm
import logging

'''
landing
'''

def landing(request):
    return render(request, 'tickets/index.html')

'''
below view is not 
needed anymore---
delete it later
'''

def create_manage(request):
    return render(request, 'tickets/user_home.html')

'''
views for
registration, login and logout
home might be deleted later
'''

def check_employee_status(user):
    return Employee.objects.filter(employee=user).exists()


def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(request, username=username, password=password)

        if user is not None:
            auth_login(request, user)
            
            # Check if the user is an employee
            try:
                employee = Employee.objects.get(employee=user)
                request.session['is_employee'] = True
                request.session['employee_role'] = employee.role
                request.session['department_assignable'] = employee.department.assignable
            except Employee.DoesNotExist:
                request.session['is_employee'] = False
                request.session['employee_role'] = None
                request.session['department_assignable'] = False

            # Check and handle any pending actions
            pending_action = request.session.pop('pending_action', None)
            if pending_action:
                if pending_action['action'] == 'update_ticket_status':
                    ticket = get_object_or_404(Ticket, pk=pending_action['ticket_pk'])
                    if employee and user == ticket.employee.employee:
                        # Update ticket status to 'in_progress'
                        open_status = Status.objects.filter(status_description='in_progress').first()
                        ticket.ticket_status = open_status
                        ticket.save()
                        messages.success(request, 'Ticket status updated successfully.')

            # redirect to the next URL or a default URL
            next_url = request.GET.get('next', 'department_selection')
            return redirect(next_url)

        else:
            # Handle invalid login attempt
            context = {'error': 'Invalid username or password'}
            return render(request, 'tickets/login.html', context)
    else:
        return render(request, 'tickets/login.html')



def get_employee_role(user):
    try:
        employee = Employee.objects.get(employee=user)
        if employee.role == 'manager' and employee.department is None:
            return 'super_manager'
        return employee.role
    except Employee.DoesNotExist:
        return None

@login_required
def home(request):
    user = request.user
    if hasattr(user, 'employee') and user.employee.role == 'manager':
        return render(request, 'tickets/manager_home.html')
    else:
        return render(request, 'tickets/staff_home.html')

def register_view(request):
    if request.method == 'POST':                           # http request method - pulls data from server
        form = CustomUserForm(request.POST)                # starts the form using the request - with POST data
        if form.is_valid():
            user =  form.save()                            # saves form (in db) upon validation
            auth_login(request, user)
            return redirect('department_selection')
    else:
        form = CustomUserForm()                           # for request method GET 
    context = { 
        'form':form
    }
    return render(
        request, 
        'tickets/register.html', 
        context
    )           # renders registr. template


def logout_view(request):
    logout(request)
    return render(request, 'tickets/logout.html')

'''
department specific views
- department selection during ticket creation
- create ticket for specific department
'''

@login_required
def department_selection(request):
    allowed_departments = ['IT', 'Engineering', 'HR']
    departments = Department.objects.filter(
        department_name__in = allowed_departments,
        assignable=True
    )

    context = {
        'departments': departments
    }
    return render(
        request,
        'tickets/department_selection.html',
        context
    )

# separate function for sending email notifications
logger = logging.getLogger(__name__)

@login_required
def department_ticket_creation(request):

    department_id = request.GET.get("department")
    department = get_object_or_404(Department, id=department_id)

    if request.method == "POST":
        logger.debug("POST request received")
        logger.debug(f"POST data: {request.POST}")
        logger.debug(f"FILES data: {request.FILES}")
        print(request.POST)
        selected_employee = request.POST.get("employee")
        employee = get_object_or_404(Employee, id=selected_employee)
        print(employee)
        print("hello")
        ticket_form = TicketForm(
            request.POST,
            request.FILES,
        )
        # print(ticket_form)
        recurring_ticket_form = RecurringTicketForm(
            request.POST, is_recurring=request.POST.get("is_recurring") == "on"
        )  # Pass is_recurring to the form

        if ticket_form.is_valid():
            try:
                logger.debug("Ticket form is valid, attempting to save")
                ticket = ticket_form.save(commit=False)
                ticket.request_user = request.user
                ticket.department = department
                ticket.employee = employee
                # print("hello")
                # selected_employee = ticket_form.cleaned_data.get("employee")

                # logger.debug(f"Selected employee: {selected_employee}")
                # logger.debug(f"Request user: {request.user}")

                # if selected_employee.employee == request.user:
                #     logger.debug("User attempted to assign ticket to themselves")
                #     messages.warning(request, "You are assigning ticket to yourself.")

                # Save the ticket regardless of the employee assignment
                ticket.save()
                logger.debug(f"Ticket saved with ID: {ticket.id}")

                # Handle file upload
                files = request.FILES.getlist("documents")
                for file in files:
                    document = Documents.objects.create(ticket=ticket, document=file)
                    logger.debug(f"Document created: {document.id}")

                # Handle recurring ticket if selected
                is_recurring = request.POST.get("is_recurring") == "on"
                logger.debug(
                    f"Is recurring checkbox status: {'checked' if is_recurring else 'unchecked'}"
                )

                if is_recurring:
                    logger.debug(
                        f"Is recurring form valid: {recurring_ticket_form.is_valid()}"
                    )
                    if recurring_ticket_form.is_valid():
                        recurring_ticket = recurring_ticket_form.save(commit=False)
                        recurring_ticket.recurring_description = (
                            ticket.ticket_description
                        )
                        recurring_ticket.employee = selected_employee
                        recurring_ticket.department = department
                        recurring_ticket.save()
                        logger.debug(
                            f"Recurring ticket saved with ID: {recurring_ticket.id}"
                        )
                    else:
                        logger.debug(
                            f"Recurring form errors: {recurring_ticket_form.errors}"
                        )
                        messages.warning(
                            request,
                            "Ticket created, but failed to create recurring ticket. Please check the details.",
                        )

                messages.success(
                    request,
                    f"Your ticket has been successfully created and sent to {department.department_name}.",
                )
                logger.debug("Redirecting to department selection")
                return redirect("department_selection")
            except Exception as e:
                logger.exception("Exception occurred while creating ticket")
                messages.error(request, f"Failed to create ticket: {str(e)}")
        else:
            messages.error(
                request, "Form submission failed. Please check the form details."
            )
            print(ticket_form.errors)
    else:
        ticket_form = TicketForm(department=department, user=request.user)
        recurring_ticket_form = RecurringTicketForm()

    context = {
        "ticket_form": ticket_form,
        "recurring_ticket_form": recurring_ticket_form,
        "department": department,
    }
    return render(request, "tickets/department_ticket_creation.html", context)


'''
ticket management views
- create ticket
- update ticket (update message later !?)
- delete ticket
- created tickets message

'''

@login_required
def manage_tickets(request):

    return render(request, 'tickets/manage_tickets.html')

@login_required
def get_manage_tickets(request):
    user = request.user
    search_query = request.GET.get('search', '')  # get the search query from the request
    tickets = Ticket.objects.filter(
        request_user=user
    )
    
    if search_query:
        tickets = tickets.filter(
            ticket_description__icontains=search_query
        )
    
    open_tickets = tickets.exclude(
        ticket_status__status_description='closed')[:3]  # slice open tickets to first 3

    closed_tickets = tickets.filter(
        ticket_status__status_description='closed')[:3]    # closed tickets to first 3
    ticket_comments = TicketCommentsForm()

    one_week_ago = timezone.now() - timedelta(weeks=1)
    
    context = {
        'open_tickets': open_tickets,
        'closed_tickets': closed_tickets,
        'search_query': search_query,
        'ticket_comments' : ticket_comments,
        'one_week_ago': one_week_ago
    }

    return render(
        request, 
        'tickets/partials/ticket_list_user.html',
         context
    )  # return only the ticket list fragment for HTMX request

'''
tickets open longer 
than 5 days, supermanager's view
'''

def open_tickets_over_5_days(request):
    user = request.user
    employee = Employee.objects.get(
        employee=user
    )

    if user.is_authenticated and employee.role == 'super_manager':
        five_days_ago = timezone.now() - timedelta(days=5)
        data = Ticket.objects.filter(
            created_at__lte=five_days_ago,
            ticket_status__status_description='open'
        ).values('employee__department__department_name').annotate(open_tickets_count=Count('id')).order_by('employee__department__department_name')

        return JsonResponse(
            list( data ), 
            safe=False
        )
    return JsonResponse(
        {'error': 'Unauthorized access'},
         status=401
    )

'''
tickets open longer 
than 5 days, manager's view
'''

def manager_open_tickets_over_5_days(request):
    user = request.user
    employee = Employee.objects.get(
        employee=user
    )
    if user.is_authenticated and employee.role == 'manager':
        five_days_ago = timezone.now() - timedelta(days=5)
        data = Ticket.objects.filter(
            created_at__lte=five_days_ago,
            ticket_status__status_description='open',
            department=request.user.employee.department
        ).values('employee.department').annotate(open_tickets_count=Count('id')).order_by('employee.department')

        print(f'\n the data: {data}\n')
        return JsonResponse(list(data), safe=False)
    
    return JsonResponse({'error': 'Unauthorized access'}, status=401)

@login_required
def create_ticket(request):
    if request.method == 'POST':
        form = TicketForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                request.session['ticket_data'] = form.cleaned_data # save the ticket form data to session
                return redirect('department_selection')         # redirect to department selection
            except Exception as e:
                messages.error(request, f'Failed to create ticket: {str(e)}')
    else:
        form = TicketForm()

    context = {
        'form': form,
    }
    return render(
        request,
        'tickets/create_ticket.html',
        context
    )


def remove_document(request, document_id):
    if request.method == 'POST':
        document = Documents.objects.get(id=document_id)
        document.delete()
        return JsonResponse({'success': True})
    return JsonResponse({'success': False})

def create_recurring_ticket(request):
    if request.method == 'POST':
        form = RecurringTicketForm(request.POST)
        if form.is_valid():
            form.save()
            if request.is_ajax():  # check if the request is AJAX
                return JsonResponse({'success': True})
            else:
                return redirect('ticket-list')  # redirect target
        else:
            if request.is_ajax():
                return JsonResponse({'success': False, 'errors': form.errors})
    else:
        form = RecurringTicketForm()
    context = {
        'form': form
    }

    return render(
        request, 
        'tickets/recurring_ticket_form.html',
        context
    )

@login_required
def ticket_created(request):

    context = {
        'success_message': "Your ticket has been successfully created and sent to the department.",
    }
    return render(request, 'tickets/ticket_created.html', context)
    

@login_required
def ticket_update(request, pk):
    ticket = get_object_or_404(Ticket, pk=pk)
    user = request.user

    try:
        employee = Employee.objects.get(employee=user)
        user_role = employee.role
    except Employee.DoesNotExist:
        user_role = 'user'

    if request.method == 'POST':
        form = TicketForm(
            request.POST,
            request.FILES,  # Include file data in the form
            instance=ticket,
            department=ticket.employee.department,
            user_role=user_role,
            form_type='update'
        )

        if form.is_valid():
            updated_ticket = form.save(commit=False)
            
            # Get the changed fields but exclude 'documents'
            update_fields = [field for field in form.changed_data if field != 'documents']
            if 'ticket_status' in form.cleaned_data:
                updated_ticket.ticket_status = form.cleaned_data['ticket_status']

                if updated_ticket.ticket_status.status_description == 'closed' and not form.cleaned_data.get('ticket_resolution'):
                    messages.error(request, 'Please provide a resolution before closing the ticket.')
                    form.add_error('ticket_resolution', 'Please provide a resolution before closing the ticket.')

                    context = {
                        'form': form,
                        'ticket': updated_ticket,
                    }
                    return render(request, 'tickets/ticket_update.html', context)

            if 'ticket_resolution' in form.cleaned_data:
                updated_ticket.ticket_resolution = form.cleaned_data['ticket_resolution']
            
            updated_ticket.save(update_fields=update_fields)
            messages.success(request, 'Ticket updated successfully.')
            return redirect('ticket_detail', pk=ticket.pk)

        else:
            messages.error(request, 'Form submission failed. Please check the form details.')

    else:
        form = TicketForm(
            instance=ticket,
            department=ticket.employee.department,
            user_role=user_role,
            form_type='update'
        )

    context = {
        'form': form,
        'ticket': ticket,
    }
    return render(
        request, 
        'tickets/ticket_update.html',
        context
    )
def ticket_status_redirect(request, pk):
    ticket = get_object_or_404(Ticket, pk=pk)

    if request.user.is_authenticated:
        if request.user == ticket.employee.employee:
            # Update status directly if the user is authenticated and authorized
            open_status = Status.objects.filter(status_description='in_progress').first()
            ticket.ticket_status = open_status
            ticket.save()
            messages.success(request, 'Ticket status updated successfully.')
            return redirect(reverse('ticket_detail', args=[pk]))
        else:
            # Save action and parameters in session
            request.session['pending_action'] = {
                'action': 'update_ticket_status',
                'ticket_pk': pk,
            }
            logout(request)
            login_url = reverse('login') + '?next=' + reverse('ticket_status_redirect', args=[pk])
            return redirect(login_url)
    else:
        # Save action and parameters in session
        request.session['pending_action'] = {
            'action': 'update_ticket_status',
            'ticket_pk': pk,
        }
        login_url = reverse('login') + '?next=' + reverse('ticket_status_redirect', args=[pk])
        return redirect(login_url)


@login_required
def ticket_delete(request, pk):
    ticket = get_object_or_404(
                Ticket,
                pk = pk,
                request_user = request.user
    )
    if request.method == 'POST':
        ticket.delete()       
        return('manage_tickets')

    context = {
            'ticket': ticket
    }
    return render(request, 'tickets/ticket_delete.html', context)

'''
ticket comments
'''

@login_required
def ticket_detail(request, pk):
    ticket = get_object_or_404(Ticket, pk=pk)
    comments = ticket.comments.all()
    comment_form = TicketCommentsForm()

    # Fetch the department of the user who created the ticket
    creator_department = ticket.request_user.get_department()

    print(f'Department of the user who created the ticket: {creator_department}')

    if request.method == 'POST':
        form = TicketCommentsForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.user = request.user
            comment.ticket = ticket
            comment.save()
            return HttpResponseRedirect(reverse('ticket_detail', args=[pk]))

    context = {
        'ticket': ticket,
        'comments': comments,
        'comment_form': comment_form,
        'creator_department': creator_department,
    }
    return render(
        request, 
        'tickets/ticket_detail.html',
        context
    )

'''

def ticket_reopen(request, pk):
    ticket = get_object_or_404(Ticket, pk=pk)

    if request.user != ticket.request_user:
        messages.error(request, 'You do not have permission to reopen this ticket.')
        return redirect('manage_tickets')

    if ticket.ticket_status.status_description == 'closed':
        if ticket.updated_at and timezone.now() <= ticket.updated_at + timedelta(weeks=1):
            open_status = Status.objects.filter(status_description='open', department=ticket.employee.department).first()
            if open_status:
                ticket.ticket_status = open_status
                ticket.save()
                messages.success(request, 'Ticket reopened successfully.')
            else:
                messages.error(request, 'Open status not found.')
        else:
            messages.warning(request, 'This ticket cannot be reopened as it was closed more than a week ago.')
    else:
        messages.warning(request, 'This ticket is not closed.')

    return redirect('manage_tickets')
'''

@login_required
def ticket_reopen(request, pk):
    ticket = get_object_or_404(Ticket, pk=pk)

    if request.user != ticket.request_user:
        messages.error(request, 'You do not have permission to reopen this ticket.')
        return redirect('manage_tickets')

    if ticket.ticket_status.status_description == 'closed':
        if ticket.updated_at and timezone.now() <= ticket.updated_at + timedelta(weeks=1):
            open_status = Status.objects.filter(status_description='open', department=ticket.employee.department).first()
            if open_status:
                ticket.ticket_status = open_status
                ticket.save()
                messages.success(request, 'Ticket reopened successfully.')
            else:
                messages.error(request, 'Open status not found.')
        else:
            messages.warning(request, 'This ticket cannot be reopened as it was closed more than a week ago.')
    else:
        messages.warning(request, 'This ticket is not closed.')

    return redirect('manage_tickets')

def reopen_ticket_redirect(request, pk):
    if request.user.is_authenticated:
        return ticket_reopen(request, pk)
    else:
        login_url = reverse('login') + '?next=' + reverse('reopen_ticket', args=[pk])
        return redirect(login_url)

@login_required
def add_comment(request, ticket_id):
    ticket = get_object_or_404(Ticket, id=ticket_id)

    if request.method == 'POST':
        form = TicketCommentsForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.user = request.user
            comment.ticket = ticket
            comment.save()
            messages.success(request, 'Comment added successfully.')

            comments = ticket.comments.all()  # get updated comments
            context = {'comments': comments, 'ticket': ticket}

            return render_to_string(
                'tickets/partials/comment.html', 
                context, 
                request=request
            )

        else:
            messages.error(request, 'Failed to add comment. Please check the form.')

    return JsonResponse(
        {   'error': 'Invalid request method or comment form error' }
    )

def employee_dashboard(request):
    user = request.user
    view = request.GET.get('view', 'assigned')  # default to 'assigned' view
    search_query = request.GET.get('search', '')

    try:
        employee = Employee.objects.get(employee=user)
        department = employee.department

        # Check if the department is assignable
        is_department_assignable = department.assignable if department else False

        # Determine which tickets to fetch based on view and employee role
        if view == 'all_departments' and employee.role == 'super_manager':
            tickets = Ticket.objects.select_related('employee__department').all()
        elif view == 'department' and employee.role == 'manager':
            if is_department_assignable:
                # Tickets assigned to the manager's employees
                tickets = Ticket.objects.filter(employee__in=department.department_employees.all())
            else:
                # All tickets created by employees in the department
                tickets = Ticket.objects.filter(request_user__in=department.department_employees.values('employee'))
        elif view == 'created' and employee.role == 'super_manager':
            tickets = Ticket.objects.filter(request_user=user)
        elif employee.role == 'manager' and not is_department_assignable:
            # All tickets created by employees in the department
            tickets = Ticket.objects.filter(request_user__in=department.department_employees.values('employee'))
        elif is_department_assignable or view != 'assigned':
            tickets = Ticket.objects.filter(employee=employee)
        else:
            tickets = Ticket.objects.none()  # No tickets for non-assignable departments if viewing 'assigned'

        # Apply search filter
        if search_query:
            tickets = tickets.filter(
                Q(ticket_description__icontains=search_query) |
                Q(employee__employee__first_name__icontains=search_query) |
                Q(employee__employee__last_name__icontains=search_query)
            )

        # Pagination
        paginator = Paginator(tickets, 3)  # show 3 tickets per page
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)

        # Prepare context
        if view == 'all_departments' and employee.role == 'super_manager':
            department_tickets = defaultdict(list)
            for ticket in page_obj:
                department_tickets[ticket.employee.department.department_name].append(ticket)
            context = {
                'employee': employee,
                'department_tickets': dict(department_tickets),
                'view': view,
                'search_query': search_query,
                'page_obj': page_obj,
            }
        else:
            context = {
                'employee': employee,
                'assigned_tickets': page_obj,
                'view': view,
                'search_query': search_query,
                'page_obj': page_obj,
            }
    except Employee.DoesNotExist:
        context = {
            'assigned_tickets': [],
            'view': view,
        }

    # Render for HTMX requests or standard requests
    if request.htmx:
        return render(
            request,
            'tickets/partials/ticket_list.html',
            context
        )
    
    return render(
        request,
        'tickets/employee_dashboard.html',
        context
    )

    
def get_assigned_tickets(employee):
    if employee.role == 'manager':
        assigned_tickets = Ticket.objects.filter(
            employee__department=employee.department
        )
    else:
        assigned_tickets = Ticket.objects.filter(
            employee=employee
        )
    return assigned_tickets

    
def get_assigned_tickets(employee):
    if employee.role == 'manager':
        assigned_tickets = Ticket.objects.filter(
            employee__department=employee.department
        )
    else:
        assigned_tickets = Ticket.objects.filter(
            employee=employee
        )
    return assigned_tickets

def assign_ticketcounts(request):
    user = request.user
    try:
        employee = Employee.objects.get(employee=user)
        if employee.role == 'manager':
            # managers see all tickets in their department
            assigned_tickets = Ticket.objects.filter(
                employee__department=employee.department
            )
        else:
            # staff and interns see only their assigned tickets
            assigned_tickets = Ticket.objects.filter(
                employee=employee
            )
    
    except Employee.DoesNotExist:
        assigned_tickets = []

    if assigned_tickets.count() > 0:

            return HttpResponse(
            f'''<span 
                    hx-get="/assign_ticketcounts" 
                    hx-swap="outerHTML" 
                    hx-trigger="every 60s" 
                    class="position-absolute \
                    top-0 start-100 translate-middle\
                    badge rounded-pill bg-secondary text-white" 
                    style=" margin-left: 1px;
                    margin-right: 10px;
                    margin-top:-5px;"> { assigned_tickets.count() }
                </span>'''
            )
    else:
        return HttpResponse(
        f'''<span 
                hx-get="/myticket_counts" 
                hx-swap="outerHTML" 
                hx-trigger="every 60s">
            </span>'''
        )

def myticket_counts(request):
    user = request.user
    tickets = Ticket.objects.filter(request_user=user)
    if tickets.count() > 0:

        return HttpResponse(
        f'''<span 
                hx-get="/myticket_counts" 
                hx-swap="outerHTML" 
                hx-trigger="every 60s" 
                class="position-absolute \
                top-0 start-100 translate-middle\
                badge rounded-pill bg-secondary text-white" 
                style=" margin-left: 1px;
                margin-right: 10px;
                margin-top:-5px;"> { tickets.count() }
            </span>'''
        )

    else:
        return HttpResponse(
        f'''<span 
                hx-get="/myticket_counts" 
                hx-swap="outerHTML" 
                hx-trigger="every 60s">
            </span>'''
        )
        
def department_ticket_stats(request):
    status_counts = Ticket.objects.values(
        'ticket_status__status_description').annotate(count=Count('id'))

    return JsonResponse(list(status_counts), safe=False)

def tickets_by_status(request):
    status = request.GET.get('status')

    if status:
        tickets = Ticket.objects.filter(ticket_status__status_description=status)
        ticket_data = [
            {
                'id': ticket.id,
                'ticket_description': ticket.ticket_description,
                'employee_name': ticket.employee.employee.get_full_name(),  # adjust as per your model structure
                'created_at': ticket.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            }
            for ticket in tickets
        ]
        return JsonResponse(ticket_data, safe=False)

    return JsonResponse([], safe=False)

'''
service rating view
'''

def rate_service(request, ticket_id):
    ticket = get_object_or_404(Ticket, id=ticket_id)

    if request.method == 'POST':
        form = ServiceRatingForm(request.POST)
        if form.is_valid():
            rating = form.save(commit=False)
            rating.ticket = ticket
            rating.user = request.user
            rating.save()
            messages.success(request, 'Thank you for your feedback!')
            return redirect('manage_tickets')  # Redirect to a relevant page after rating
    else:
        form = ServiceRatingForm()

    context = {
        'form': form,
        'ticket': ticket
    }

    return render(
        request, 
        'tickets/rate_service.html', 
        context
    )