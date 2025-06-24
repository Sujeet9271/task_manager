# filters.py
import django_filters
from board.models import Task
from django.db.models import Q

class TaskFilter(django_filters.FilterSet):
    search = django_filters.CharFilter(label='Search',method='filter_search')
    due_before = django_filters.DateFilter(label='Due Before',field_name='due_date', lookup_expr='lte')
    due_after = django_filters.DateFilter(label='Due After',field_name='due_date', lookup_expr='gte',)
    assigned_to = django_filters.BaseInFilter(label='Assigned To',field_name='assigned_to__id', lookup_expr='in')
    tags = django_filters.BaseInFilter(label='Tags',field_name='labels__id', lookup_expr='in')

    class Meta:
        model = Task
        fields = ['priority', 'is_complete']

    def filter_search(self, queryset, name, value):
        return queryset.filter(
            Q(title__icontains=value) | Q(description__icontains=value)
        )
