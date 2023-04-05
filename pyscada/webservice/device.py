# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from pyscada.utils.scheduler import SingleDeviceDAQProcess
from pyscada.models import DeviceWriteTask, DeviceReadTask
from pyscada.device import GenericDevice
from .models import WebServiceAction
from . import PROTOCOL_ID
from .devices import GenericDevice as GenericHandlerDevice

from django.db.models import Q

from time import time
import sys

import logging

logger = logging.getLogger(__name__)
driver_ok = True


class Device(GenericDevice):
    """
    WebService device
    """

    def __init__(self, device):
        self.driver_ok = driver_ok
        self.handler_class = GenericHandlerDevice
        super().__init__(device)
        self.webservices = {}

        if not self.driver_handler_ok:
            logger.warning(f'Cannot import handler for {self.device}')

        for var in self.device.variable_set.filter(active=1):
            if not hasattr(var, 'webservicevariable'):
                continue
            self.variables[var.pk] = {}
            self.variables[var.pk]['object'] = var
            self.variables[var.pk]['value'] = None
            for ws in var.ws_variables.filter(active=1, webservice_RW=0):
                try:
                    self.webservices[ws.pk]['object']
                except KeyError:
                    self.webservices[ws.pk] = {}
                    self.webservices[ws.pk]['object'] = ws
                    self.webservices[ws.pk]['variables'] = {}
                    self.webservices[ws.pk]['variable_properties'] = {}
                self.webservices[ws.pk]['variables'][var.pk] = {}
                self.webservices[ws.pk]['variables'][var.pk]['object'] = var
                self.webservices[ws.pk]['variables'][var.pk]['value'] = None
                self.webservices[ws.pk]['variables'][var.pk]['device_path'] = var.device.webservicedevice.url
                self.webservices[ws.pk]['variables'][var.pk]['proxy'] = var.device.webservicedevice.http_proxy
                self.webservices[ws.pk]['variables'][var.pk]['variable_path'] = var.webservicevariable.path

            for vp in var.variableproperty_set.all():
                if not hasattr(vp.variable, 'webservicevariable'):
                    continue
                for ws in vp.ws_variable_properties.filter(active=1, webservice_RW=0):
                    try:
                        self.webservices[ws.pk]['object']
                    except KeyError:
                        self.webservices[ws.pk] = {}
                        self.webservices[ws.pk]['object'] = ws
                        self.webservices[ws.pk]['variables'] = {}
                        self.webservices[ws.pk]['variable_properties'] = {}
                    self.webservices[ws.pk]['variable_properties'][vp.pk] = {}
                    self.webservices[ws.pk]['variable_properties'][vp.pk]['object'] = vp
                    self.webservices[ws.pk]['variable_properties'][vp.pk]['value'] = None
                    self.webservices[ws.pk]['variable_properties'][vp.pk]['device_path'] = vp.variable.device.webservicedevice.url
                    self.webservices[ws.pk]['variable_properties'][vp.pk]['proxy'] = vp.variable.device.webservicedevice.http_proxy
                    self.webservices[ws.pk]['variable_properties'][vp.pk]['variable_path'] = vp.variable.webservicevariable.path

        self._h.set_webservices(self.webservices)

    def request_data(self):
        output = []

        if not self.driver_ok or not self.driver_handler_ok:
            return output

        output = self._h.read_data_all(self.variables)

        return output

    def write_data(self, variable_id, value, task):
        """
        write value to a WebService
        """

        output = []

        if variable_id not in self.variables:
            return False

        if not self.variables[variable_id]['object'].writeable:
            return False

        if value is not None and self.variables[variable_id]['object'].update_value(value, time()):
            output.append(self.variables[variable_id]['object'].create_recorded_data_element())

        return output


class Process(SingleDeviceDAQProcess):
    device_filter = dict(webservicedevice__isnull=False, protocol_id=PROTOCOL_ID)
    bp_label = 'pyscada.webservice-%s'

    def __init__(self, dt=5, **kwargs):
        self.last_query = 0
        self.dt_query_data = 0
        self.device = None
        self.device_id = None
        self.ws_write_todo = []
        super(SingleDeviceDAQProcess, self).__init__(dt=dt, **kwargs)

    def loop(self):
        # data from a write
        data = []

        # process webservice task
        if len(self.ws_write_todo) > 0:
            for ws_id in self.ws_write_todo:
                WebServiceAction.objects.get(id=ws_id).write_data()
                cwt = DeviceWriteTask(variable_id=WebServiceAction.objects.get(id=ws_id).write_trigger.pk, value=0,
                                      start=time(),
                                      user=DeviceWriteTask.objects.filter(
                                          done=True,
                                          variable=WebServiceAction.objects.get(id=ws_id).write_trigger).latest('start')
                                      .user)
                cwt.create_and_notificate(cwt)
        self.ws_write_todo = []

        # process write tasks
        # Do all the write task for this device starting with the oldest
        for task in DeviceWriteTask.objects.filter(Q(done=False, start__lte=time(), failed=False,) & (Q(variable__device_id=self.device_id) | Q(variable_property__variable__device_id=self.device_id))).order_by('start'):
            if task.variable.scaling is not None:
                task.value = task.variable.scaling.scale_output_value(task.value)
            tmp_data = self.device.write_data(task.variable.id, task.value, task)
            if isinstance(tmp_data, list):
                if len(tmp_data) > 0:
                    if hasattr(task.variable, 'webservicevariable') and task.value:
                        for ws in task.variable.ws_write_trigger.filter(active=1, webservice_RW=1,
                                                                        write_trigger=task.variable):
                            self.ws_write_todo.append(ws.pk)
                    task.done = True
                    task.finished = time()
                    task.save()
                    data.append(tmp_data)
                else:
                    task.failed = True
                    task.finished = time()
                    task.save()
            else:
                task.failed = True
                task.finished = time()
                task.save()
        if isinstance(data, list):
            if len(data) > 0:
                return 1, data

        device_read_tasks = DeviceReadTask.objects.filter(Q(done=False, start__lte=time(), failed=False,) & (Q(device_id=self.device_id) | Q(variable__device_id=self.device_id) | Q(variable_property__variable__device_id=self.device_id)))

        if time() - self.last_query > self.dt_query_data or len(device_read_tasks):
            self.last_query = time()
            # Query data
            if self.device is not None:
                tmp_data = self.device.request_data()
                if isinstance(tmp_data, list):
                    if len(tmp_data) > 0:
                        device_read_tasks.update(done=True, finished=time())
                        return 1, [tmp_data, ]

            device_read_tasks.update(failed=True, finished=time())

        return 1, None
