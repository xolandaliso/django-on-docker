
from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit, Layout, Field
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import Permission
from .models import (
    CustomUser, Department, Employee, Type, Location, 
    Ticket, TicketComments, Documents
)

class CustomUserForm(UserCreationForm):
    #department = forms.ModelChoiceField(queryset=Department.objects.all(), required=True)
    #role = forms.ChoiceField(choices=Employee.ROLE_CHOICES, required=True)

    class Meta(UserCreationForm.Meta):
        model = CustomUser
        fields = [ 'username', 'email', 'phone', 'pbx_extension',\
                     'is_active' ]

    def __init__(self, *args, **kwargs):
        super(CustomUserForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.add_input(Submit('submit', 'Register', css_class='btn-primary'))
        self.helper.layout = Layout(
            Field('username', css_class='form-control'),
            Field('email', css_class='form-control'),
            Field('phone', css_class='form-control'),
            Field('pbx_extension', css_class='form-control'),
            #Field('department', css_class='form-control'),
            #Field('role', css_class='form-control'),
        )

    def save(self, commit=True):
        user = super(CustomUserForm, self).save(commit=False)
        if commit:
            user.save()
            print(f"User saved with username: {user.username}, role: {self.cleaned_data.get('role')}")
            department = self.cleaned_data.get('department')
            role = self.cleaned_data.get('role')
            Employee.objects.create(employee=user, department=department, role=role)
            self.assign_permissions(user, role)  # Assign permissions based on role
        return user

    def assign_permissions(self, user, role):
        if role == 'manager':
            manager_permissions = Permission.objects.filter(name__in=['Can view ticket', 'Can change ticket'])
            user.user_permissions.add(*manager_permissions)
            print(f"Added manager permissions to user: {user.username}")
        elif role == 'staff':
            staff_permissions = Permission.objects.filter(name='Can change ticket')
            user.user_permissions.add(*staff_permissions)
            print(f"Added staff permissions to user: {user.username}")


class TicketForm(forms.ModelForm):

    documents = forms.FileField(
                widget=forms.ClearableFileInput(),
                     required=False )    #for documents 

    #recurring_ticket = forms.ModelChoiceField(
                        #queryset=RecurringTicket.objects.all(), \
                             #required=False )    # for recurring tickets 

    class Meta:
        model = Ticket
        fields = [
            'ticket_description',
            'ticket_type',
            'location',
        ]
        widgets = {
            'ticket_description': forms.Textarea(attrs={'rows': 4}),
        }

    def __init__(self, *args, **kwargs):
        super(TicketForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.add_input(Submit('submit', 'Submit', css_class='btn-primary'))

    def save(self, commit=True):
        ticket = super(TicketForm, self).save(commit=False)
        if commit:
            ticket.save()
            self.save_documents(ticket)
            self.save_recurring_ticket(ticket)
        return ticket

    def save_documents(self, ticket):
        documents = self.cleaned_data.get('documents')
        if documents:
            for document in documents:
                Documents.objects.create(ticket=ticket, document=document)

    '''
    def save_recurring_ticket(self, ticket):
        recurring_ticket = self.cleaned_data.get('recurring_ticket')
        if recurring_ticket:
            ticket.recurring_ticket = recurring_ticket
            ticket.save()
    '''