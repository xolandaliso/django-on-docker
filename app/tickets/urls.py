from . import views
from django.urls import path
from django.contrib.auth import views as auth_views

from django.contrib.auth.views import (
    LogoutView, 
    PasswordResetView, 
    PasswordResetDoneView, 
    PasswordResetConfirmView,
    PasswordResetCompleteView
)


urlpatterns = [
    path('', views.login_view, name='landing'),  # landing page
    path('login/', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('home/', views.home, name='home'),
    path('create_ticket/', views.create_ticket, name='create_ticket'),
    path('create_manage/', views.create_manage, name='create_manage'),
    path('ticket_created/', views.ticket_created, name='ticket_created'),
    path('department_selection/', views.department_selection, name='department_selection'),
    path('department_ticket_creation/', views.department_ticket_creation, name='department_ticket_creation'),
    path('employee_dashboard/', views.employee_dashboard, name='employee_dashboard'),
    path('manage_tickets/', views.manage_tickets, name='manage_tickets'),
    path('ticket/<int:pk>/update/', views.ticket_update, name='ticket_update'),
    path('ticket/<int:pk>/delete/', views.ticket_delete, name='ticket_delete'),
    path('logout/', views.logout_view, name='logout'),

]

# password reset urls

password_patterns = [
    path('password-reset/', PasswordResetView.as_view(template_name='password/password_reset.html',  html_email_template_name='password/password_reset_email.html'),name='password-reset'),
    path('password-reset/done/', PasswordResetDoneView.as_view(template_name='password/password_reset_done.html'),name='password_reset_done'),
    path('password-reset-confirm/<uidb64>/<token>/', PasswordResetConfirmView.as_view(template_name='password/password_reset_confirm.html'),name='password_reset_confirm'),
    path('password-reset-complete/',PasswordResetCompleteView.as_view(template_name='password/password_reset_complete.html'),name='password_reset_complete'),
]

urlpatterns += password_patterns

htmx_urlpatterns = [
    path('get_manage_tickets/', views.get_manage_tickets, name='get_manage_tickets'),
    path('ticket/<int:pk>/', views.ticket_detail, name='ticket_detail'),
    path('ticket/<int:ticket_id>/add_comment/', views.add_comment, name='add_comment'),
    path('mytickets_counts/', views.myticket_counts, name='myticket_counts'),
    path('assign_ticketcounts/', views.assign_ticketcounts, name='assign_ticketcounts'),
    path('department/ticket_stats/', views.department_ticket_stats, name='department_ticket_stats'),
    path('department/tickets/', views.tickets_by_status, name='tickets_by_status'),
    path('ticket/<int:pk>/reopen/', views.ticket_reopen, name='ticket_reopen'),
    path('department/open_tickets_over_5_days/', views.open_tickets_over_5_days, name='open_tickets_over_5_days'),
    path('department/manager_open_tickets_over_5_days/', views.manager_open_tickets_over_5_days, name='manager_open_tickets_over_5_days'),
    path('reopen-ticket/<int:pk>/', views.reopen_ticket_redirect, name='reopen_ticket'),
    path('rate-service/<int:ticket_id>/', views.rate_service, name='rate_service'),
    path('ticket-status/<int:pk>/', views.ticket_status_redirect, name='ticket_status_redirect'),
    path('document/remove/<int:document_id>/', views.remove_document, name='remove_document'),
    path('recurring-ticket/create/', views.create_recurring_ticket, name='create_recurring_ticket'),

]

urlpatterns += htmx_urlpatterns

