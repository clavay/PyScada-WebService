# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from pyscada.models import Device
from pyscada.models import Variable

import requests

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
    http_proxy = models.CharField(max_length=254, null=True, blank=True)

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
                paths[variables[var_id]['device_path'] + self.path]['proxy'] = variables[var_id]['proxy']
            except KeyError as e:
                paths[variables[var_id]['device_path'] + self.path] = {}
                paths[variables[var_id]['device_path'] + self.path][var_id] = variables[var_id]['variable_path']
                paths[variables[var_id]['device_path'] + self.path]['proxy'] = variables[var_id]['proxy']
        for ws_path in paths:
            out[ws_path] = {}
            try:
                if paths[ws_path]['proxy'] is not None:
                    proxy_dict = {
                        "http": paths[ws_path]['proxy'],
                        "https": paths[ws_path]['proxy'],
                        "ftp": paths[ws_path]['proxy']
                    }
                    res = requests.get(ws_path, proxies=proxy_dict)
                else:
                    res = requests.get(ws_path)
            except Exception as e:
                res = None
                out[ws_path]["content_type"] = None
                out[ws_path]["ws_path"] = ws_path
                logger.debug(e)
                pass
            if res is not None and res.status_code == 200:
                out[ws_path]["content_type"] = res.headers['Content-type']
                out[ws_path]["ws_path"] = ws_path
                if "text/xml" in out[ws_path]["content_type"]:
                    out[ws_path]["result"] = ET.fromstring(res.text)
                elif "application/json" in out[ws_path]["content_type"]:
                    out[ws_path]["result"] = res.json()
            elif res is not None:
                logger.debug(str(ws_path) + " - status code = " + str(res.status_code))
                pass
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
                logger.warning("WebService Write action with id " + str(self.id) +
                               " have variables with different devices")
            if var.query_prev_value():
                path = path.replace("$" + str(var.id), str(var.prev_value))
            else:
                logger.debug("WS Write - Var " + var + " has no prev value")
                return False
        ws_path = device.webservicedevice.ip_or_dns + path
        try:
            res = requests.get(ws_path)
        except:
            res = None
        if res is not None and res.status_code == 200:
            return True
        else:
            if res is None:
                logger.debug("WS Write - res is None")
            else:
                logger.debug("WS Write - res code is " + str(res.status_code))
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

    def path(self):
        return self.webservicevariable.path
