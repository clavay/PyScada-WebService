# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from .. import PROTOCOL_ID
from pyscada.models import DeviceProtocol

from django.conf import settings

from time import time

import logging

logger = logging.getLogger(__name__)


class GenericDevice:
    def __init__(self, pyscada_device, variables, webservices):
        self._device = pyscada_device
        self._variables = variables
        self._webservices = webservices
        self.inst = None

    def connect(self):
        """
        establish a connection to the Instrument
        """
        return None

    def disconnect(self):
        """
        close the connection to the Instrument
        """
        return None

    def before_read(self):
        """
        will be called before the first read_data
        """
        return None

    def after_read(self):
        """
        will be called after the last read_data
        """
        return None

    def read_data(self, variable_instance):
        """
        read values from the device
        """
        return None

    def read_data_and_time(self, ws_action_id, device):
        """
        read values and timestamps from the device
        """
        return self.read_data(ws_action_id), self.time()

    def write_data(self, variable_id, value, task):
        """
        write values to the device
        """
        return False

    def time(self):
        return time()
