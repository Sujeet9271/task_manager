from django.contrib import admin
from django.db.models import ForeignKey, ManyToManyField
from django.apps import apps
from django.utils.html import format_html
from board.forms import TagForm
from board.models import Tag
from task_manager.logger import logger
import sys





app_name = sys.modules[__name__].__package__.split('.')[0]
app_config = apps.get_app_config(app_name)
class MyModelAdmin(admin.ModelAdmin):
    show_full_result_count = False
    list_per_page = 100
    list_max_show_all = 200

    def __init__(self, model, admin_site):
        super().__init__(model, admin_site)
        
        # Automatically set all ForeignKey fields to raw_id_fields
        self.raw_id_fields = [
            field.name
            for field in model._meta.get_fields()
            if isinstance(field, ForeignKey)
        ]

        self.list_select_related = [
            field.name
            for field in model._meta.get_fields()
            if isinstance(field, ForeignKey)
        ]

        self.filter_horizontal = [field.name for field in model._meta.get_fields() if isinstance(field, ManyToManyField)]


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    form = TagForm 

    list_display = ('colored_name', 'created_by', 'is_deleted')
    list_filter = ('created_by', 'is_deleted')
    search_fields = ('name', 'created_by__username', 'created_by__email')
    ordering = ('name',)
    list_per_page = 25

    def colored_name(self, obj):
        return format_html(
            '<span style="color: {}; font-weight: bold;">#{}</span>',
            obj.color,
            obj.name
        )
    colored_name.short_description = 'Name'


for model in app_config.get_models():
    try:
        admin.site.register(model,MyModelAdmin)
    except admin.sites.AlreadyRegistered:
        pass

