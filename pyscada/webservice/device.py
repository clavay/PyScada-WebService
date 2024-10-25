# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from pyscada.utils.scheduler import SingleDeviceDAQProcess
from pyscada.models import DeviceWriteTask, DeviceReadTask
from pyscada.device import GenericDevice
from . import PROTOCOL_ID
from .devices import GenericDevice as GenericHandlerDevice

from django.db.models import Q

from time import time
import sys

driver_ok = True
try:
    import requests
except ImportError:
    logger.error("Cannot import requests", exc_info=True)
    driver_ok = False
try:
    import defusedxml.ElementTree as ET
except ImportError:
    logger.error("Cannot import defusedxml", exc_info=True)
    driver_ok = False
try:
    from json.decoder import JSONDecodeError
except ImportError:
    logger.error("Cannot import json", exc_info=True)
    driver_ok = False

import logging

logger = logging.getLogger(__name__)


class Device(GenericDevice):
    """
    WebService device
    """

    def __init__(self, device):
        self.driver_ok = driver_ok
        self.handler_class = GenericHandlerDevice
        super().__init__(device)

    def write_data(self, variable_id, value, task):
        return self._h.write_data(variable_id, value, task)
