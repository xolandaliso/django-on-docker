from django import forms
from django.utils import timezone
from django.contrib.auth.forms import UserCreationForm
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Row, Column, Submit, Field, Div
from .models import CustomUser, Resolution, Ticket, \
Employee, Documents, Status, TicketComments, Type, ServiceRating, Department, RecurringTicket
import logging


class CustomUserForm(UserCreationForm):
    department = forms.ModelChoiceField(
        queryset=Department.objects.all(),
        required=True,
        widget=forms.Select(attrs={'placeholder': 'Select Department'})
    )

    def __init__(self, *args, **kwargs):
        super(CustomUserForm, self).__init__(*args, **kwargs)
        self.fields['first_name'].required = True
        self.fields['last_name'].required = True
        self.fields['department'].required = True
        self.fields['password1'].help_text = ''

        # Add placeholders and remove labels
        fields = ['first_name', 'last_name', 'username', 'email', 'phone', 'pbx_extension', 'password1', 'password2']
        for field in fields:
            self.fields[field].widget.attrs['placeholder'] = self.fields[field].label
            self.fields[field].label = ''

        self.fields['password1'].widget.attrs['placeholder'] = 'Password'
        self.fields['password2'].widget.attrs['placeholder'] = 'Confirm Password'
        self.fields['department'].label = ''

        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.add_input(Submit('submit', 'Register', css_class='btn-secondary'))
        self.helper.layout = Layout(
            Div(
                Div(Field('first_name', css_class='form-control'), css_class='col-md-6'),
                Div(Field('last_name', css_class='form-control'), css_class='col-md-6'),
                css_class='row mb-3'
            ),
            Div(
                Div(Field('username', css_class='form-control'), css_class='col-md-6'),
                Div(Field('email', css_class='form-control'), css_class='col-md-6'),
                css_class='row mb-3'
            ),
            Div(
                Div(Field('department'), css_class='col-md-4'),
                Div(Field('phone', css_class='form-control'), css_class='col-md-4'),
                Div(Field('pbx_extension', css_class='form-control form-control-sm'), css_class='col-md-4'),
                css_class='row mb-3'
            ),
            Div(
                Div(Field('password1', css_class='form-control'), css_class='col-md-6'),
                Div(Field('password2', css_class='form-control'), css_class='col-md-6'),
                css_class='row mb-3'
            )
        )

    class Meta(UserCreationForm.Meta):
        model = CustomUser
        fields = ['first_name', 'last_name', 'username', 'email', 'phone', 'pbx_extension', 'department']

    def save(self, commit=True):
        user = super(CustomUserForm, self).save(commit=False)
        user.is_active = True
        user.default_department = self.cleaned_data.get('department')
        
        if commit:
            user.save()
            # create Employee instance
            Employee.create_employee(user, user.default_department)
        
        return user

'''
custom multiple file upload
widget
'''

class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput())
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single_file_clean = super().clean
        if isinstance(data, (list, tuple)):
            result = [single_file_clean(d, initial) for d in data]
        else:
            result = single_file_clean(data, initial)
        return result


class TicketForm(forms.ModelForm):
    documents = MultipleFileField(label="Attach Documents", required=False)

    class Meta:
        model = Ticket
        fields = ["ticket_description", "ticket_type", "location", "employee"]

    def __init__(self, *args, **kwargs):
        department = kwargs.pop("department", None)
        user_role = kwargs.pop("user_role", None)
        form_type = kwargs.pop("form_type", "create")
        user = kwargs.pop("user", None)
        employee = kwargs.pop("employee", None)

        super(TicketForm, self).__init__(*args, **kwargs)

        if department:
            self.fields["employee"].queryset = Employee.objects.filter(
                department=department, on_leave=False
            )
            self.fields["ticket_type"].queryset = Type.objects.filter(
                department=department
            )

            if form_type == "create" and "update":
                self.fields["employee"].queryset = self.fields[
                    "employee"
                ].queryset.exclude(role="super_manager")

        self.helper = FormHelper()
        self.helper.form_method = "post"

        if form_type == "update" and user_role in ["staff", "manager", "super_manager"]:
            self.fields["ticket_status"] = forms.ModelChoiceField(
                queryset=Status.objects.filter(department=department),
                required=False,
                empty_label="Select status",
                label="Ticket Status",
            )
            self.fields["ticket_resolution"] = forms.ModelChoiceField(
                queryset=Resolution.objects.filter(department=department),
                required=False,
                empty_label="Select resolution",
                label="Ticket Resolution",
            )
            self.fields["ticket_status"].label_from_instance = lambda obj: dict(
                Status.STATUS_CHOICES
            ).get(obj.status_description, obj.get_status_description_display())

            self.helper.layout = Layout(
                Field("ticket_description", css_class="form-control"),
                Field("ticket_type", css_class="form-control"),
                Field("location", css_class="form-control"),
                Field("employee", css_class="form-control"),
                "ticket_status",
                Field(
                    "ticket_resolution",
                    css_class="form-control",
                    id="id_ticket_resolution",
                    style="display:none;",
                ),
                "documents",
                Submit("submit", "Update Ticket", css_class="btn btn-primary"),
            )
        else:
            self.helper.layout = Layout(
                Field("ticket_description", css_class="form-control"),
                Field("ticket_type", css_class="form-control"),
                Field("location", css_class="form-control"),
                Field("employee", css_class="form-control"),
                "documents",
                Submit("submit", "Create Ticket", css_class="btn btn-primary"),
            )

        if user_role not in ["staff", "manager", "super_manager"]:
            self.fields.pop("ticket_status", None)
            self.fields.pop("ticket_resolution", None)

    def save(self, commit=True, department=None):
        ticket = super(TicketForm, self).save(commit=False)

        if self.instance.pk is None:  # Creating a new ticket
            open_status = Status.objects.filter(
                status_description="open", department=department
            ).first()
            # if open_status:
            ticket.ticket_status = open_status

        if commit:
            ticket.save(department=department)

            # Handle file uploads
            if "documents" in self.files:
                documents = self.files.getlist("documents")
                for document in documents:
                    Documents.objects.create(ticket=ticket, document=document)

        return ticket

        
class RecurringTicketForm(forms.ModelForm):
    class Meta:
        model = RecurringTicket
        fields = ['frequency']
        widgets = {
            'frequency': forms.Select(attrs={'class': 'form-control select'}),
        }

    def __init__(self, *args, is_recurring=False, **kwargs):
        super(RecurringTicketForm, self).__init__(*args, **kwargs)
        self.fields['custom_interval'] = forms.IntegerField(required=False, widget=forms.NumberInput(attrs={'class': 'form-control'}))
        self.fields['custom_unit'] = forms.ChoiceField(
            choices=[('hours', 'Hours'), ('days', 'Days'), ('months', 'Months')],
            required=False,
            widget=forms.Select(attrs={'class': 'form-control'})
        )

        # Set default frequency to an empty string
        self.initial['frequency'] = ''

        # Optionally, make frequency conditionally required based on is_recurring (if needed)
        if is_recurring:
            self.fields['frequency'].required = True

    def clean(self):
        cleaned_data = super().clean()
        frequency = cleaned_data.get('frequency')
        custom_interval = cleaned_data.get('custom_interval')
        custom_unit = cleaned_data.get('custom_unit')

        if frequency == 'custom':
            if not custom_interval or not custom_unit:
                raise forms.ValidationError("Custom interval and unit are required when selecting custom frequency.")
        else:
            cleaned_data['custom_interval'] = None
            cleaned_data['custom_unit'] = None

        return cleaned_data
    def save(self, commit=True):
        instance = super(RecurringTicketForm, self).save(commit=False)
        instance.custom_interval = self.cleaned_data.get('custom_interval')
        instance.custom_unit = self.cleaned_data.get('custom_unit')
        instance.next_run = instance.calculate_next_run()
        if commit:
            instance.save()
        return instance

class TicketCommentsForm(forms.ModelForm):
    class Meta:
        model = TicketComments
        fields = ['comment']

        def __init__(self, *args, **kwargs):
            super(TicketCommentsForm, self).__init__(*args, **kwargs)
            self.helper = FormHelper()
            self.helper.form_method = 'post'
            self.helper.add_input(Submit('submit', 'Add Comment', css_class='btn btn-secondary mt-2'))
            self.helper.layout = Layout(
                Field('comment', css_class='form-control', rows=3)
        )

class ServiceRatingForm(forms.ModelForm):
    class Meta:
        model = ServiceRating
        fields = ['rating', 'feedback']