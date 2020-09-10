# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from pyscada.models import Device
from pyscada.models import Variable

from urllib.request import urlopen

import json
import xml.etree.ElementTree as ET

from django.db import models
from django.utils.encoding import python_2_unicode_compatible
from django.db.models.signals import post_save

import logging

logger = logging.getLogger(__name__)


@python_2_unicode_compatible
class WebServiceDevice(models.Model):
    webservice_device = models.OneToOneField(Device, null=True, blank=True, on_delete=models.CASCADE)
    ip_or_dns = models.CharField(max_length=254)

    def __str__(self):
        return self.webservice_device.short_name


@python_2_unicode_compatible
class WebServiceVariable(models.Model):
    webservice_variable = models.OneToOneField(Variable, null=True, blank=True, on_delete=models.CASCADE)
    path = models.CharField(max_length=254, null=True, blank=True,
                            help_text="look at the readme")

    def __str__(self):
        return self.id.__str__() + "-" + self.webservice_variable.short_name


@python_2_unicode_compatible
class WebServiceAction(models.Model):
    name = models.CharField(max_length=254)
    webservice_mode_choices = ((0, 'Path'), (1, 'GET'), (2, 'POST'),)
    webservice_mode = models.PositiveSmallIntegerField(default=0, choices=webservice_mode_choices)
    webservice_RW_choices = ((0, 'Read'), (1, 'Write'),)
    webservice_RW = models.PositiveSmallIntegerField(default=0, choices=webservice_RW_choices)
    write_trigger = models.ForeignKey(Variable, null=True, blank=True, on_delete=models.CASCADE,
                                      related_name="ws_write_trigger")
    path = models.CharField(max_length=400, null=True, blank=True, help_text="look at the readme")
    variables = models.ManyToManyField(Variable, related_name="ws_variables")
    active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

    def request_data(self, variables):
        paths = {}
        out = {}
        for var_id in variables:
            try:
                paths[variables[var_id]['device_path'] + self.path][var_id] = variables[var_id]['variable_path']
            except KeyError:
                paths[variables[var_id]['device_path'] + self.path] = {}
                paths[variables[var_id]['device_path'] + self.path][var_id] = variables[var_id]['variable_path']
        for ws_path in paths:
            out[ws_path] = {}
            try:
                res = urlopen(ws_path)
            except:
                res = None
                out[ws_path]["content_type"] = None
                out[ws_path]["ws_path"] = ws_path
                pass
            if res is not None and res.getcode() == 200:
                out[ws_path]["content_type"] = res.info().get_content_type()
                out[ws_path]["ws_path"] = ws_path
                if out[ws_path]["content_type"] == "text/xml":
                    out[ws_path]["result"] = ET.fromstring(res.read().decode())
                elif out[ws_path]["content_type"] == "application/json":
                    out[ws_path]["result"] = json.loads(res.read())
        return out

    def write_data(self):
        device = None
        if self.webservice_RW != 1:
            return False
        path = self.path
        for var in self.variables.all():
            if device is None:
                device = var.device
            elif device != var.device:
                logger.warning("WebService Write action with id " + self.id + " have variables with different devices")
            if var.query_prev_value():
                path = path.replace("$" + str(var.id), str(var.prev_value))
            else:
                logger.debug("WS Write - Var " + var + " has no prev value")
                return False
        ws_path = device.webservicedevice.ip_or_dns + path
        try:
            res = urlopen(ws_path)
        except:
            res = None
        if res is not None and res.getcode() == 200:
            return True
        else:
            if res is None:
                logger.debug("WS Write - res is None")
            else:
                logger.debug("WS Write - res code is " + res.getcode())
            return False

    def save(self, *args, **kwargs):
        # TODO : select only devices of selected variables
        post_save.send_robust(sender=WebServiceAction, instance=WebServiceDevice.objects.first())
        super(WebServiceAction, self).save(*args, **kwargs)


class ExtendedWebServiceDevice(Device):
    class Meta:
        proxy = True
        verbose_name = 'WebService Device'
        verbose_name_plural = 'WebService Devices'


class ExtendedWebServiceVariable(Variable):
    class Meta:
        proxy = True
        verbose_name = 'WebService Variable'
        verbose_name_plural = 'WebService Variables'
