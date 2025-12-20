from .models import SiteUpdate

def global_site_updates(request):
    """
    Makes site_updates available on EVERY page template.
    Filters based on the logged-in user's role.
    """
    if not request.user.is_authenticated:
        return {'site_updates': []}

    # Default: Get updates meant for 'all'
    audience_filters = ['all']

    # Add role-specific filters
    if request.user.role == 'student':
        audience_filters.append('student')
    elif request.user.role == 'client':
        audience_filters.append('client')
    elif request.user.role == 'donor':
        audience_filters.append('donor')
    
    # Get the latest 3 active updates
    updates = SiteUpdate.objects.filter(
        is_active=True,
        audience__in=audience_filters
    ).order_by('-created_at')[:3]

    return {'site_updates': updates}