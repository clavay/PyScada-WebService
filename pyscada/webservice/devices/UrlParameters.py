# -*- coding: utf-8 -*-
from pyscada.models import Variable, VariableHandlerParameter, DeviceHandlerParameter

import os
import logging

logger = logging.getLogger(__name__)

if os.getenv("DJANGO_SETTINGS_MODULE") is not None:
    from pyscada.webservice.devices import GenericDevice
else:
    import sys

    logger.debug("Django settings not configured.")
    GenericDevice = object
    logging.basicConfig(
        level=logging.DEBUG, handlers=[logging.StreamHandler(sys.stdout)]
    )


__author__ = "Camille Lavayssière"
__copyright__ = "Copyright 2025, Université de Pau et des Pays de l'Adour"
__credits__ = []
__license__ = "AGPLv3"
__version__ = "0.1.1"
__maintainer__ = "Camille Lavayssière"
__email__ = "clavayssiere@univ-pau.fr"
__status__ = "Beta"
__docformat__ = "reStructuredText"

pyscada_device_parameters = {"device_parameter": {"null": True}}
pyscada_variable_parameters = {"variable_parameter": {"null": True}}
pyscada_admin_content = "Configure the device url as : http://test.com/path/%device_parameter/test/%variable_parameter/pyscada<br>Set the DeviceHandlerParameter and the VariableHandlerParameter in the device and variable configurations."

class Handler(GenericDevice):
    """
    Device and variable handler to set url parameters.
    """


    def __init__(self, pyscada_device, variables):
        super().__init__(pyscada_device, variables)
        self.original_url = self._device.webservicedevice.url

    def read_data_all(self, variables_dict, erase_cache=False):
        output = []

        for item in variables_dict.values():
            if item.readable:
                value, read_time = self.read_data_and_time(item)
                if (
                    value is not None
                    and read_time is not None
                    and item.update_values(
                        value, read_time, erase_cache=erase_cache
                    )
                ):
                    output.append(item)
            self.after_read()

        return output

    def read_data(self, variable_instance):
        wd = self._device.webservicedevice
        wd.url = self.original_url

        dhps = DeviceHandlerParameter.objects.filter(instrument=self._device)
        device_parameter = None
        for dhp in dhps:
            if dhp.name == "device_parameter":
                device_parameter = dhp
                break

        vhps = VariableHandlerParameter.objects.filter(variable=variable_instance)
        variable_parameter = None
        for vhp in vhps:
            if vhp.name == "variable_parameter":
                variable_parameter = vhp
                break

        if device_parameter is not None and variable_parameter is not None:
            wd.url = wd.url.replace("%device_parameter", device_parameter.value).replace("%variable_parameter", variable_parameter.value)
            logger.debug(wd.url)
        else:
            logger.warning(f"Cannot get the device or variable parameters : {device_parameter} {variable_parameter}")

        self.before_read()

        return super().read_data(variable_instance)
