# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from pyscada.models import Device
from pyscada.models import Variable

from urllib.request import urlopen

import json
import xml.etree.ElementTree as ET

from django.db import models
from django.utils.encoding import python_2_unicode_compatible
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
                            help_text="For XML look at "
                                      "https://docs.python.org/3/library/xml.etree.elementtree.html#xpath-support -"
                                      " for JSON write nested dict as a space separated string : dict1 dict2 ...")

    def __str__(self):
        return self.id.__str__() + "-" + self.webservice_variable.short_name


@python_2_unicode_compatible
class WebServiceAction(models.Model):
    name = models.CharField(max_length=254)
    webservice_mode_choices = ((0, 'Path'), (1, 'GET'), (2, 'POST'),)
    webservice_mode = models.PositiveSmallIntegerField(default=0, choices=webservice_mode_choices)
    path = models.CharField(max_length=400, null=True, blank=True)
    variables = models.ManyToManyField(Variable)
    active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

    def request_data(self, variables):
        paths = {}
        out = {}
        #for var in self.variables.all():
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
                out[ws_path]["content_type"] = None
                out[ws_path]["ws_path"] = ws_path
                pass
            if res.getcode() == 200:
                out[ws_path]["content_type"] = res.info().get_content_type()
                out[ws_path]["ws_path"] = ws_path
                if out[ws_path]["content_type"] == "text/xml":
                    out[ws_path]["result"] = ET.fromstring(res.read().decode())
                elif out[ws_path]["content_type"] == "application/json":
                    out[ws_path]["result"] = json.loads(res.read())
        return out


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
