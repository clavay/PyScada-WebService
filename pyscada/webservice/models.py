# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from pyscada.models import Device, DeviceHandler
from pyscada.models import Variable, VariableProperty
from . import PROTOCOL_ID

from django.db import models

import requests
import defusedxml.ElementTree as ET
from json.decoder import JSONDecodeError

import logging

logger = logging.getLogger(__name__)


class WebServiceDevice(models.Model):
    webservice_device = models.OneToOneField(
        Device, null=True, blank=True, on_delete=models.CASCADE
    )
    url = models.URLField(max_length=254)
    http_proxy = models.CharField(max_length=254, null=True, blank=True)
    webservice_mode_choices = (
        (0, "Path"),
        (1, "GET"),
        (2, "POST"),
    )
    webservice_mode = models.PositiveSmallIntegerField(
        default=0, choices=webservice_mode_choices
    )
    webservice_content_type_choices = (
        (0, "Auto"),
        (1, "text/xml"),
        (2, "application/json"),
    )
    webservice_content_type = models.PositiveSmallIntegerField(
        default=0, choices=webservice_content_type_choices
    )
    headers = models.CharField(
        max_length=400,
        null=True,
        blank=True,
        help_text="For exemple: {'Authorization': 'TOKEN', 'Content-Type': 'application/json',}",
    )
    payload = models.CharField(
        max_length=400,
        null=True,
        blank=True,
        help_text="For exemple: {'type': 'consumption_load_curve', 'usage_point_id': 'ID',}",
    )

    protocol_id = PROTOCOL_ID

    def parent_device(self):
        try:
            return self.webservice_device
        except:
            return None

    def __str__(self):
        return self.webservice_device.short_name


class WebServiceVariable(models.Model):
    webservice_variable = models.OneToOneField(
        Variable, null=True, blank=True, on_delete=models.CASCADE
    )
    path = models.CharField(
        max_length=254, null=True, blank=True, help_text="look at the readme"
    )

    protocol_id = PROTOCOL_ID

    def __str__(self):
        return self.id.__str__() + "-" + self.webservice_variable.name


class ExtendedWebServiceDevice(Device):
    class Meta:
        proxy = True
        verbose_name = "WebService Device"
        verbose_name_plural = "WebService Devices"


class ExtendedWebServiceVariable(Variable):
    class Meta:
        proxy = True
        verbose_name = "WebService Variable"
        verbose_name_plural = "WebService Variables"

    def path(self):
        return self.webservicevariable.path
