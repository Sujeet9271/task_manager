from django.contrib import admin
from django.db.models import ForeignKey, ManyToManyField
from django.apps import apps
from notifications.models import Notification
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

    
@admin.register(Notification)
class NotificationAdmin(MyModelAdmin):
    list_filter = ['notification_type','content_type','created_at','read']


for model in app_config.get_models():
    try:
        admin.site.register(model,MyModelAdmin)
    except admin.sites.AlreadyRegistered:
        pass

