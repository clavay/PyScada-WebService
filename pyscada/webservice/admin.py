# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from pyscada.webservice import PROTOCOL_ID
from pyscada.webservice.models import WebServiceDevice, ExtendedWebServiceDevice
from pyscada.webservice.models import WebServiceVariable, ExtendedWebServiceVariable
from pyscada.webservice.models import WebServiceAction
from pyscada.admin import DeviceAdmin
from pyscada.admin import VariableAdmin
from pyscada.admin import admin_site
from pyscada.models import Device, DeviceProtocol, Variable, VariableProperty
from django.contrib import admin
import logging

logger = logging.getLogger(__name__)


class WebServiceDeviceAdminInline(admin.StackedInline):
    model = WebServiceDevice


class WebServiceDeviceAdmin(DeviceAdmin):
    save_as = True
    save_as_continue = True

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'protocol':
            kwargs['queryset'] = DeviceProtocol.objects.filter(pk=PROTOCOL_ID)
            db_field.default = PROTOCOL_ID
        return super(WebServiceDeviceAdmin, self).formfield_for_foreignkey(db_field, request, **kwargs)

    def get_queryset(self, request):
        """Limit Pages to those that belong to the request's user."""
        qs = super(WebServiceDeviceAdmin, self).get_queryset(request)
        return qs.filter(protocol_id=PROTOCOL_ID)

    inlines = [
        WebServiceDeviceAdminInline
    ]


class WebServiceVariableAdminInline(admin.StackedInline):
    model = WebServiceVariable


class WebServiceVariableAdmin(VariableAdmin):
    list_display = ('id', 'name', 'description', 'unit', 'device', 'value_class', 'active', 'writeable', 'path')
    list_editable = ('unit', 'device', 'value_class', 'active', 'writeable')
    list_display_links = ('name',)
    save_as = True
    save_as_continue = True

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'device':
            kwargs['queryset'] = Device.objects.filter(protocol=PROTOCOL_ID)
        return super(WebServiceVariableAdmin, self).formfield_for_foreignkey(db_field, request, **kwargs)

    def get_queryset(self, request):
        """Limit Pages to those that belong to the request's user."""
        qs = super(WebServiceVariableAdmin, self).get_queryset(request)
        return qs.filter(device__protocol_id=PROTOCOL_ID)

    inlines = [
        WebServiceVariableAdminInline
    ]


class WebServiceActionAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'webservice_mode', 'path')
    filter_horizontal = ('variables', 'variable_properties',)
    save_as = True
    save_as_continue = True

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        if db_field.name == 'variables':
            kwargs['queryset'] = Variable.objects.filter(device__protocol_id=PROTOCOL_ID)
        elif db_field.name == 'variable_properties':
            kwargs['queryset'] = VariableProperty.objects.filter(variable__device__protocol_id=PROTOCOL_ID)
        return super().formfield_for_manytomany(db_field, request, **kwargs)


# admin_site.register(ExtendedWebServiceDevice, WebServiceDeviceAdmin)
# admin_site.register(ExtendedWebServiceVariable, WebServiceVariableAdmin)
admin_site.register(WebServiceAction, WebServiceActionAdmin)
