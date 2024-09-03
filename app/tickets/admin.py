from django.contrib import admin
from django.db import models
from .models import Department, Employee, Ticket,\
     Status, Type, Resolution, CustomUser, Documents, RecurringTicket

# Register your models here.

class TicketAdmin(admin.ModelAdmin):
    # ... other admin configurations ...

    formfield_overrides = {
        models.ForeignKey: {'queryset': Status.objects.all()},
    }

class DocumentsAdmin(admin.ModelAdmin):
    list_display = ('ticket', 'document')
    search_fields = ('ticket__id', 'document')

class RecurringTicketAdmin(admin.ModelAdmin):
    list_display = ('recurring_description', 'employee', 'frequency', 'next_run')
    list_filter = ('frequency', 'employee')

admin.site.register(CustomUser)
admin.site.register(Ticket, TicketAdmin)
admin.site.register(Status)
admin.site.register(Department)
admin.site.register(Employee)
admin.site.register(Type)
admin.site.register(Resolution)
admin.site.register(Documents, DocumentsAdmin)
admin.site.register(RecurringTicket, RecurringTicketAdmin) 
