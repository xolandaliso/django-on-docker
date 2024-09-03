from .models import Ticket

def ticket_count(request):
    if request.user.is_authenticated:
        ticket_count = Ticket.objects.filter(request_user=request.user).count()
    else:
        ticket_count = 0
    return {'ticket_count': ticket_count}