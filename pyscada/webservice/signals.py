# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from pyscada.models import Device, Variable
from pyscada.webservice.models import WebServiceDevice, WebServiceVariable, ExtendedWebServiceVariable, \
    ExtendedWebServiceDevice, WebServiceAction

from django.dispatch import receiver
from django.db.models.signals import post_save
import logging

logger = logging.getLogger(__name__)


@receiver(post_save, sender=WebServiceDevice)
@receiver(post_save, sender=WebServiceVariable)
@receiver(post_save, sender=WebServiceAction)
@receiver(post_save, sender=ExtendedWebServiceVariable)
@receiver(post_save, sender=ExtendedWebServiceDevice)
def _reinit_daq_daemons(sender, instance, **kwargs):
    """
    update the daq daemon configuration when changes be applied in the models
    """
    if type(instance) is WebServiceDevice:
        post_save.send_robust(sender=Device, instance=instance.webservice_device)
    elif type(instance) is WebServiceVariable:
        post_save.send_robust(sender=Variable, instance=instance.webservice_variable)
    elif type(instance) is WebServiceAction:
        device_list = set()
        for var in instance.variables.all():
            device_list.add(var.device)
        for vp in instance.variable_properties.all():
            device_list.add(vp.varriable.device)
        for d in device_list:
            try:
                post_save.send_robust(sender=Device, instance=d)
            except AttributeError:
                logger.debug('Sending signal from WebServiceAction failed for %s : not a WebService Device' % d)
    elif type(instance) is ExtendedWebServiceVariable:
        post_save.send_robust(sender=Variable, instance=Variable.objects.get(pk=instance.pk))
    elif type(instance) is ExtendedWebServiceDevice:
        post_save.send_robust(sender=Device, instance=Device.objects.get(pk=instance.pk))
