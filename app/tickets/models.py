

from tracemalloc import stop
from django.db import models
from django.utils import timezone
from datetime import timedelta
from django.conf import settings
from django.contrib.auth.models import AbstractUser, Group, Permission, User

class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        abstract = True

class CustomUser(AbstractUser, TimeStampedModel):
    phone = models.CharField(max_length=15, blank=True, null=True)
    pbx_extension = models.CharField(max_length=10, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    default_department = models.ForeignKey(
        'Department',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='default_users'
    )

    groups = models.ManyToManyField(
        Group,
        related_name='customuser_group',
        blank=True,
        help_text='The groups this user belongs to. A user will get all permissions granted to each of their groups.',
        verbose_name='groups',
    )   

    user_permissions = models.ManyToManyField(
        Permission,
        related_name='customuser_permissions', 
        blank=True,
        help_text='Specific permissions for this user.',
        verbose_name='user permissions',
    )

    def __str__(self):
        return self.username 

    def get_department(self):
        try:
            employee = self.employee_roles.first()
            if employee:
                return employee.department
            return self.default_department
        except Employee.DoesNotExist:
            return self.default_department
    '''
    def open_tickets(self):
        open_tickets = Ticket.objects.filter()
    def assigned_tickets():
    '''
               
class Department(TimeStampedModel):

    department_name = models.CharField(max_length=255)
    employees = models.ManyToManyField( 
                    'CustomUser', 
                    through='Employee', 
                    related_name='departments'
    )
    assignable = models.BooleanField(default=False)

    def __str__(self):

        return self.department_name

class Employee(TimeStampedModel):
    ROLE_CHOICES = [
        ('manager', 'Manager'), 
        ('staff', 'Staff'),
        ('intern', 'Intern'),
        ('super_manager', 'Super Manager')
    ]
   
    employee = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='employee_roles')
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='department_employees')
    role = models.CharField(max_length=50, choices=ROLE_CHOICES)
    on_leave = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.employee.username} - {self.department.department_name}"

    @classmethod
    def create_employee(cls, user, department, role='staff'):
        return cls.objects.create(
            employee=user,
            department=department,
            role=role
        )

        
class Type(models.Model):
    type_description = models.CharField(max_length=255)
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='department_type')

    def __str__(self):
        return self.type_description
        
class Resolution(models.Model):
    resolution_description = models.CharField(max_length=255)
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='department_resolution')


    def __str__(self):
        return self.resolution_description

class Status(models.Model):

    STATUS_CHOICES = [
        ('open', 'Open'),
        ('in_progress', 'In Progress'),
        ('closed', 'Closed'),
    ]

    status_description = models.CharField(max_length=255, choices=STATUS_CHOICES)
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='department_status')

    class Meta:
        unique_together = ('status_description', 'department')  

    def __str__(self):
        return self.status_description

class Location(models.Model):
    location_name = models.CharField(max_length=255)
    location_description = models.TextField(blank=True, null=True)
    location_parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='sublocations')

    def __str__(self):
        return self.location_name       
 
class Ticket(TimeStampedModel):

    request_user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='requested_tickets')
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='assigned_tickets')
    ticket_description = models.TextField()
    ticket_type = models.ForeignKey(Type, on_delete=models.CASCADE, related_name='tickets', null=True, blank=True)
    ticket_resolution = models.ForeignKey(Resolution, on_delete=models.CASCADE, related_name='tickets', null=True, blank=True)
    ticket_status = models.ForeignKey(Status, on_delete=models.CASCADE, related_name='tickets', null=True, blank=True)
    location = models.ForeignKey(Location, on_delete=models.CASCADE, related_name='tickets', null=True, blank=True)

    def __str__(self):
        return f"Ticket {self.id}" # by {self.request_user.username}
    '''
    def save(self, *args, **kwargs):
        if not self.pk and not self.ticket_status:
            open_status = Status.objects.get(status_description='open')
            self.ticket_status = open_status
        super().save(*args, **kwargs)
    '''

class ServiceRating(TimeStampedModel):
    RATING_CHOICES = [
        (1, 'Extremely Poor'),
        (2, 'Poor'),
        (3, 'Neutral'),
        (4, 'Good'),
        (5, 'Excellent'),
    ]

    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name='service_ratings')
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='service_ratings')
    rating = models.PositiveIntegerField(choices=RATING_CHOICES)  # Use the descriptive choices
    feedback = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Rating {self.rating} for Ticket {self.ticket.id} by {self.user.username}"

class TicketComments(TimeStampedModel):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='comments')
    comment = models.TextField()

    def __str__(self):
        return f"Comment by {self.user.username} on Ticket {self.ticket.id}"       
           
class Documents(TimeStampedModel):
    ticket = models.ForeignKey(Ticket, on_delete=models.CASCADE, related_name='documents')
    document = models.FileField(upload_to='documents/')

    def __str__(self):
        return f"Document for Ticket {self.ticket.id}"

class RecurringTicket(models.Model):
    FREQUENCY_CHOICES = [
        ('daily', 'Daily'),
        ('weekly', 'Weekly'),
        ('monthly', 'Monthly'),
        ('yearly', 'Yearly'),
        ('custom', 'Custom'),
    ]

    UNIT_CHOICES = [
        ('days', 'Days'),
        ('weeks', 'Weeks'),
        ('months', 'Months'),
    ]

    recurring_description = models.TextField()
    frequency = models.CharField(max_length=50, choices=FREQUENCY_CHOICES)
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='recurring_tickets')
    requester = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='requested_recurring_tickets', null=True, blank=True)
    custom_interval = models.PositiveIntegerField(null=True, blank=True)
    custom_unit = models.CharField(max_length=50, choices=UNIT_CHOICES, null=True, blank=True)
    next_run = models.DateTimeField()

    def __str__(self):
        return f"Recurring Ticket by {self.employee.employee.username} - {self.frequency}"

    def calculate_next_run(self):
        if self.frequency == 'daily':
            return timezone.now() + timedelta(days=1)
        elif self.frequency == 'weekly':
            return timezone.now() + timedelta(weeks=1)
        elif self.frequency == 'monthly':
            return timezone.now() + timedelta(days=30)  
        elif self.frequency == 'yearly':
            return timezone.now() + timedelta(days=365)
        elif self.frequency == 'custom' and self.custom_interval and self.custom_unit:
            if self.custom_unit == 'days':
                return timezone.now() + timedelta(days=self.custom_interval)
            elif self.custom_unit == 'weeks':
                return timezone.now() + timedelta(weeks=self.custom_interval)
            elif self.custom_unit == 'months':
                return timezone.now() + timedelta(days=30 * self.custom_interval)  
        else:
            print(f'the frequency, unit, and interval: {self.frequency,  self.custom_interval, self.custom_unit:}')
            raise ValueError("Invalid frequency or custom interval/unit")
        return self.next_run  # fallback

    def save(self, *args, **kwargs):
        if not self.next_run:
            self.next_run = self.calculate_next_run()
        super().save(*args, **kwargs)

    def get_requester_department(self):
        if self.requester:
            return self.requester.get_department()
        return None