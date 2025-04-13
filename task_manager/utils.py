from django.contrib.sites.models import Site
from django.urls import reverse

def get_full_url(viewname, args=None, kwargs=None):
    current_site = Site.objects.get_current()
    domain = current_site.domain
    path = reverse(viewname, args=args, kwargs=kwargs)
    return f"{domain}{path}"
