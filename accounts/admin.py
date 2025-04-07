from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.db.models import ForeignKey, ManyToManyField
from django.apps import apps
from accounts.models import Users
from task_manager.logger import logger
import sys

app_name = sys.modules[__name__].__package__.split('.')[0]
app_config = apps.get_app_config(app_name)

@admin.register(Users)
class UserADmin(UserAdmin):
    list_display=['id','email','username','name', 'is_staff','is_active','date_joined']
    list_display_links=['id','email',]
    list_filter = ['is_active','is_staff','is_superuser','date_joined']
    readonly_fields = ('date_joined','last_login')
    search_fields = ['email','name','username']
    filter_horizontal = ('groups', 'user_permissions',)

    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal info', {'fields': ('username', 'name', )}),
        ('Permissions', {
            'fields': ('is_active', 'is_staff', 'is_superuser','groups', 'user_permissions',),
        }),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )


    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username','email','name','password1', 'password2','is_staff'),
        }),
    )

    def get_fieldsets(self, request, obj=None):
        if not obj:
            return self.add_fieldsets
        else:
            return super().get_fieldsets(request, obj)


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
            if isinstance(field, ForeignKey)  and field.name in self.list_display
        ]

        self.filter_horizontal = [field.name for field in model._meta.get_fields() if isinstance(field, ManyToManyField)]


for model in app_config.get_models():
    try:
        admin.site.register(model,MyModelAdmin)
    except admin.sites.AlreadyRegistered:
        pass

