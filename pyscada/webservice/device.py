# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from pyscada.utils.scheduler import SingleDeviceDAQProcess
from pyscada.models import DeviceWriteTask, DeviceReadTask
from .models import WebServiceAction
from pyscada.webservice import PROTOCOL_ID

from django.db.models import Q

from time import time

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

    def request_data(self):
        if self.device.webservicedevice.web_service_handler is None:
            return self._request_data()
        elif self.device.webservicedevice.web_service_handler.handler_path is not None:
            sys.path.append(self.device.webservicedevice.web_service_handler.handler_path)

        try:
            mod = __import__(self.device.webservicedevice.web_service_handler.handler_class, fromlist=['Handler'])
            device_handler = getattr(mod, 'Handler')
            self._h = device_handler(self.device, self.variables, self.webservices)
            self.driver_handler_ok = True
        except ImportError:
            self.driver_handler_ok = False
            logger.error("Handler import error : %s" % self.device.short_name)
            return None

        if self.driver_handler_ok:
            return self._request_data_handler()

    def _request_data_handler(self):
        """
        request data from the instrument/device
        """
        output = []

        self._h.before_read()
        for wsa_id in self.webservices:
            res = self._h.read_data_and_time(wsa_id, self)
            for item_pk in res:
                item = self.variables[item_pk]['object']
                for (value, time) in res[item_pk]:
                        if value is not None and item.update_value(value, time):
                            output.append(item.create_recorded_data_element())
        self._h.after_read()
        return output

    def _request_data(self):

        output = []

        for item in self.webservices:
            # value = None
            res = self.webservices[item]['object'].request_data(self)
            for var in self.webservices[item]['variables']:
                path = self.webservices[item]['variables'][var]['device_path'] + self.webservices[item]['object'].path
                if self.webservices[item]['variables'][var]['value'] is not None and\
                        self.webservices[item]['object'].webservice_RW:
                    logger.warning("Variable " + str(var) + " is in more than one WebService")
                try:
                    if "text/xml" in res[path]["content_type"] or \
                            self.webservices[item]['object'].webservice_content_type == 1:
                        self.webservices[item]['variables'][var]['value'] = \
                            res[path]["result"].find(self.webservices[item]['variables'][var]['variable_path']).text
                    elif "application/json" in res[path]["content_type"] or \
                            self.webservices[item]['object'].webservice_content_type == 2:
                        tmp = res[path]["result"]
                        for key in self.webservices[item]['variables'][var]['variable_path'].split():
                            tmp = tmp.get(key, {})
                        self.webservices[item]['variables'][var]['value'] = tmp
                except KeyError:
                    logger.error("content_type missing in " + str(path) + " : " + str(res[path]))
                    self.webservices[item]['variables'][var]['value'] = None
                except TypeError:
                    self.webservices[item]['variables'][var]['value'] = None
                except AttributeError:
                    logger.error(str(path) + " : " + str(self.webservices[item]['variables'][var]['variable_path']) +
                                 " not found in " + str(res[path]["result"]))
                    self.webservices[item]['variables'][var]['value'] = None
                except SyntaxError:
                    logger.error(str(path) + " : " + str(self.webservices[item]['variables'][var]['variable_path']) +
                                 " : XPath syntax error ")
                    self.webservices[item]['variables'][var]['value'] = None
                try:
                    timestamp = time()
                    if self.webservices[item]['variables'][var]['value'] is not None \
                            and self.webservices[item]['variables'][var]['object'].\
                            update_value(float(self.webservices[item]['variables'][var]['value']), timestamp):
                        output.append(self.webservices[item]['variables'][var]['object'].create_recorded_data_element())
                except ValueError:
                    logger.debug(str(var) + " - value is : " + str(self.webservices[item]['variables'][var]['value']))
                    pass
                except TypeError:
                    logger.debug(str(var) + " - value is : " + str(self.webservices[item]['variables'][var]['value']))
                    pass

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
