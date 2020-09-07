#!/usr/bin/python
# -*- coding: utf-8 -*-

from __future__ import unicode_literals

from pyscada.utils.scheduler import SingleDeviceDAQProcessWorker
from pyscada.models import DeviceWriteTask
from .models import WebServiceAction

from time import time

import logging


logger = logging.getLogger(__name__)


class Process(SingleDeviceDAQProcessWorker):
    device_filter = dict(webservicedevice__isnull=False)
    bp_label = 'pyscada.webservice-%s'

    def __init__(self, dt=5, **kwargs):
        self.last_query = 0
        self.dt_query_data = 0
        self.device = None
        self.device_id = None
        self.ws_write_todo = []
        super(SingleDeviceDAQProcessWorker, self).__init__(dt=dt, **kwargs)

    def loop(self):
        # data from a write
        data = []

        # process webservice task
        if len(self.ws_write_todo) > 0:
            for ws_id in self.ws_write_todo:
                WebServiceAction.object.get(id=ws_id).write_data()
        self.ws_write_todo = []

        # process write tasks
        # Do all the write task for this device starting with the oldest
        for task in DeviceWriteTask.objects.filter(done=False, start__lte=time(), failed=False,
                                                   variable__device_id=self.device_id).order_by('start'):
            if task.variable.scaling is not None:
                task.value = task.variable.scaling.scale_output_value(task.value)
            tmp_data = self.device.write_data(task.variable.id, task.value, task)
            if isinstance(tmp_data, list):
                if len(tmp_data) > 0:
                    if hasattr(task.variable, 'webservicevariable') and task.value is True:
                        for ws in task.variable.webserviceaction_set.filter(active=1, webservice_RW=1,
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

        if time() - self.last_query > self.dt_query_data:
            self.last_query = time()
            # Query data
            if self.device is not None:
                tmp_data = self.device.request_data()
            else:
                return 1, None
            if isinstance(tmp_data, list):
                if len(tmp_data) > 0:
                    return 1, [tmp_data, ]

        return 1, None
