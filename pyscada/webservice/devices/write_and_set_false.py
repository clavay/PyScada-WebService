# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from pyscada.models import Variable, DeviceWriteTask
from pyscada.webservice.devices import GenericDevice

import requests
from time import time
import logging

logger = logging.getLogger(__name__)

__author__ = "Camille Lavayssière"
__copyright__ = "Copyright 2024, Université de Pau et des Pays de l'Adour"
__credits__ = []
__license__ = "AGPLv3"
__version__ = "0.1.0"
__maintainer__ = "Camille Lavayssière"
__email__ = "clavayssiere@univ-pau.fr"
__status__ = "Beta"
__docformat__ = "reStructuredText"

class Handler(GenericDevice):
    """
    Infoclimat API and other API with the same command set
    """

    def read_data_all(self, variables_dict, **kwargs):
        return []

    def write_data(self, variable_id, value, task):
        output = []
        if task.variable is None:
            return output
        wv = task.variable.webservicevariable
        wd = task.variable.device.webservicedevice
        path = wd.url
        try:
            res = requests.get(path, timeout=self.timeout)
        except:
            res = None
        if res is not None and res.status_code == 200:
            logger.error(f"Write to device {self._device} succeed : {value}")
            if self._variables[variable_id].update_values(
                [True, False], [time(), time() + 0.001]
            ):
                output.append(self._variables[variable_id])
        else:
            if res is None:
                logger.error(f"Write to device {self._device} failed, response is None")
            else:
                logger.error(
                    f"Write to device {self._device} error, response code is {res.status_code}"
                    )
        return output
