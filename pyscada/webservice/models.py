# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from pyscada.models import Device, DeviceHandler
from pyscada.models import Variable, VariableProperty
from . import PROTOCOL_ID

import requests

import defusedxml.ElementTree as ET
from json.decoder import JSONDecodeError

from django.db import models
from django.db.models.signals import post_save

import logging

logger = logging.getLogger(__name__)


class WebServiceDevice(models.Model):
    webservice_device = models.OneToOneField(Device, null=True, blank=True, on_delete=models.CASCADE)
    url = models.URLField(max_length=254)
    http_proxy = models.CharField(max_length=254, null=True, blank=True)
    web_service_handler = models.ForeignKey(DeviceHandler, null=True, blank=True, on_delete=models.SET_NULL)

    protocol_id = PROTOCOL_ID

    def parent_device(self):
        try:
            return self.webservice_device
        except:
            return None

    def __str__(self):
        return self.webservice_device.short_name


class WebServiceVariable(models.Model):
    webservice_variable = models.OneToOneField(Variable, null=True, blank=True, on_delete=models.CASCADE)
    path = models.CharField(max_length=254, null=True, blank=True,
                            help_text="look at the readme")

    protocol_id = PROTOCOL_ID

    def __str__(self):
        return self.id.__str__() + "-" + self.webservice_variable.name


class WebServiceAction(models.Model):
    name = models.CharField(max_length=254)
    webservice_mode_choices = ((0, 'Path'), (1, 'GET'), (2, 'POST'),)
    webservice_mode = models.PositiveSmallIntegerField(default=0, choices=webservice_mode_choices)
    webservice_content_type_choices = ((0, 'Auto'), (1, 'XML'), (2, 'JSON'),)
    webservice_content_type = models.PositiveSmallIntegerField(default=0, choices=webservice_content_type_choices)
    webservice_RW_choices = ((0, 'Read'), (1, 'Write'),)
    webservice_RW = models.PositiveSmallIntegerField(default=0, choices=webservice_RW_choices)
    write_trigger = models.ForeignKey(Variable, null=True, blank=True, on_delete=models.CASCADE,
                                      related_name="ws_write_trigger")
    path = models.CharField(max_length=400, null=True, blank=True, help_text="look at the readme")
    headers = models.CharField(max_length=400, null=True, blank=True, help_text="For exemple: {'Authorization': 'TOKEN', 'Content-Type': 'application/json',}")
    payload = models.CharField(max_length=400, null=True, blank=True, help_text="For exemple: {'type': 'consumption_load_curve', 'usage_point_id': 'ID',}")
    variables = models.ManyToManyField(Variable, blank=True, related_name="ws_variables")
    variable_properties = models.ManyToManyField(VariableProperty, blank=True, related_name="ws_variable_properties")
    active = models.BooleanField(default=True)

    timeout = 10
    log_error_1_count = 0
    log_error_2_count = 0

    def __str__(self):
        return self.name

    def request_data(self, device):
        variables=device.webservices[self.pk]['variables']
        variable_properties=device.webservices[self.pk]['variable_properties']
        paths = {}
        out = {}
        for var_id in variables:
            try:
                if self.path is None:
                    self.path = ''
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
                    res = requests.get(ws_path, proxies=proxy_dict, timeout=self.timeout)
                else:
                    res = requests.get(ws_path, timeout=self.timeout)
                self.log_error_1_count = 0
            except Exception as e:
                res = None
                out[ws_path]["content_type"] = None
                out[ws_path]["ws_path"] = ws_path
                if not self.log_error_1_count:
                    logger.debug(e)
                self.log_error_1_count += 1
                pass
            if res is not None and res.status_code == 200:
                out[ws_path]["content_type"] = res.headers['Content-type']
                out[ws_path]["ws_path"] = ws_path
                if "text/xml" in out[ws_path]["content_type"] or self.webservice_content_type == 1:
                    out[ws_path]["result"] = ET.fromstring(res.text)
                elif "application/json" in out[ws_path]["content_type"] or self.webservice_content_type == 2:
                    try:
                        out[ws_path]["result"] = res.json()
                        self.log_error_2_count = 0
                    except JSONDecodeError:
                        if not self.log_error_2_count:
                            logger.debug(str(ws_path) + " - JSONDecodeError : " + str(res.text))
                        self.log_error_2_count += 1
                        out[ws_path]["content_type"] = None
            elif res is not None:
                if not self.log_error_2_count:
                    logger.debug(str(ws_path) + " - status code = " + str(res.status_code))
                self.log_error_2_count += 1
            else:
                if not self.log_error_2_count:
                    logger.debug(str(ws_path) + " - get request is None")
                self.log_error_2_count += 1
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
                if var.scaling is not None:
                    var.prev_value = var.scaling.scale_output_value(var.prev_value)
                path = path.replace("$" + str(var.id), str(var.prev_value))
            else:
                logger.debug("WS Write - Var " + str(var) + " has no prev value")
                return False
        ws_path = device.webservicedevice.url + path
        try:
            res = requests.get(ws_path, timeout=self.timeout)
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
        # post_save.send_robust(sender=WebServiceAction, instance=WebServiceDevice.objects.first())
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
