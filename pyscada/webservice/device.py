# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from time import time
import json

import logging

logger = logging.getLogger(__name__)
_debug = 1


class Device:
    """
    WebService device
    """

    def __init__(self, device):
        self.variables = {}
        self.webservices = {}
        self.device = device

    def request_data(self):

        for var in self.device.variable_set.filter(active=1):
            if not hasattr(var, 'webservicevariable'):
                continue
            self.variables[var.pk] = {}
            self.variables[var.pk]['object'] = var
            self.variables[var.pk]['value'] = None
            for ws in var.webserviceaction_set.filter(active=1):
                self.webservices[ws.pk] = {}
                self.webservices[ws.pk]['object'] = ws
                self.webservices[ws.pk]['variables'] = {}
                self.webservices[ws.pk]['variables'][var.pk] = {}
                self.webservices[ws.pk]['variables'][var.pk]['object'] = var
                self.webservices[ws.pk]['variables'][var.pk]['value'] = None
                self.webservices[ws.pk]['variables'][var.pk]['device_path'] = var.device.webservicedevice.ip_or_dns
                self.webservices[ws.pk]['variables'][var.pk]['variable_path'] = var.webservicevariable.path

        output = []

        for item in self.webservices:
            timestamp = time()
            # value = None
            res = self.webservices[item]['object'].request_data(self.webservices[item]['variables'])
            for var in self.webservices[item]['variables']:
                path = self.webservices[item]['variables'][var]['device_path'] + self.webservices[item]['object'].path
                if self.webservices[item]['variables'][var]['value'] is not None:
                    logger.warning("Variable " + var + " is in more than one WebService")
                else:
                    if res[path]["content_type"] == "text/xml":
                        self.webservices[item]['variables'][var]['value'] = \
                            res[path]["result"].find(self.webservices[item]['variables'][var]['variable_path']).text
                    elif res[path]["content_type"] == "application/json":
                        tmp = res[path]["result"]
                        for key in self.webservices[item]['variables'][var]['variable_path'].split():
                            tmp = tmp.get(key, {})
                        self.webservices[item]['variables'][var]['value'] = tmp
                    if self.webservices[item]['variables'][var]['value'] is not None \
                            and self.webservices[item]['variables'][var]['object'].\
                            update_value(self.webservices[item]['variables'][var]['value'], timestamp):
                        output.append(self.webservices[item]['variables'][var]['object'].create_recorded_data_element())

        # for item in self.variables:
        # if value is not None and item.update_value(value, timestamp):
            #    output.append(item.create_recorded_data_element())

        return output

    def write_data(self, variable_id, value, task):
        """
        write value to a WebService
        """

        output = []

        for item in self.variables:
            if item.id == variable_id:
                if not item.writeable:
                    return False
                value = None
                if value is not None and item.update_value(value, time()):
                    output.append(item.create_recorded_data_element())
        return output
