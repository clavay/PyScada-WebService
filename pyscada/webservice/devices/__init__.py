# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from .. import PROTOCOL_ID
from pyscada.device import GenericHandlerDevice

import logging

logger = logging.getLogger(__name__)

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
    import json
except ImportError:
    logger.error("Cannot import json", exc_info=True)
    driver_ok = False


class GenericDevice(GenericHandlerDevice):
    def __init__(self, pyscada_device, variables):
        super().__init__(pyscada_device, variables)
        self.driver_ok = driver_ok
        self._protocol = PROTOCOL_ID
        self.last_value = None
        self.webservices = None
        self.timeout = 10
        self.log_error_1_count = 0
        self.log_error_2_count = 0
        self.result = None

    def read_data(self, variable_instance):
        """
        read values from the query result
        """
        value = None

        wv = variable_instance.webservicevariable
        wd = variable_instance.device.webservicedevice

        try:
            if wv is None:
                raise ValueError(
                    f"{variable_instance} has no webservice variable. Cannot read data from the webservice request."
                )
            if self.inst is None:
                raise ValueError(
                    f"{variable_instance.device} not connected. Cannot read data from the webservice request."
                )

            if (
                wd.webservice_content_type == 1
                or "text/xml" in self.inst.headers["Content-type"]
            ):
                value = self.result.find(variable_instance).text
            elif (
                wd.webservice_content_type == 2
                or "application/json" in self.inst.headers["Content-type"]
            ):
                tmp = self.result
                for key in wv.path.split():
                    if key.startswith("[") and key.endswith("]"):
                        try:
                            i = int(key.split("[")[1].split("]")[0])
                            tmp = tmp[i]
                        except (ValueError, IndexError) as e:
                            tmp = tmp.get(key, {})
                    else:
                        tmp = tmp.get(key, {})
                value = tmp
        except ValueError as e:
            logger.warning(e)
        except KeyError:
            logger.info(
                f"Device {self._device} - content_type missing in headers response : {self.inst.headers}"
            )
        except TypeError as e:
            logger.warning(e)
        except AttributeError as e:
            logger.warning(
                f"Device {self._device} - {wv.path} not found in {self.result} - {e}"
            )
            if type(tmp) == list:
                logger.info(
                    f"To search in json list use this syntax for the variable path : key1 key2 [list_index] key3..."
                )
        except SyntaxError as e:
            logger.warning(
                f"Device {self._device} - {wv.path} not found in {self.result} - XPath syntax error - {e}"
            )

        return value

    def connect(self):
        if super().connect() == False:
            return False

        wd = self._device.webservicedevice

        try:
            headers = json.loads(wd.headers) if wd.headers is not None else {}
            payload = json.loads(wd.payload) if wd.payload is not None else {}
            proxies = (
                {
                    "http": wd.http_proxy,
                    "https": wd.http_proxy,
                    "ftp": wd.http_proxy,
                }
                if wd.http_proxy is not None
                else {}
            )
            if wd.webservice_mode == 2:
                self.inst = requests.post(
                    wd.url,
                    data=payload,
                    headers=headers,
                    proxies=proxies,
                    timeout=self.timeout,
                )
            else:
                self.inst = requests.get(
                    wd.url,
                    params=payload,
                    headers=headers,
                    proxies=proxies,
                    timeout=self.timeout,
                )
            self.log_error_1_count = 0
            return True
        except Exception as e:
            self.inst = None
            if not self.log_error_1_count:
                logger.debug(e)
            self.log_error_1_count += 1
        return False

    def before_read(self):
        if not super().before_read():
            return False
        self.accessibility()

        wd = self._device.webservicedevice

        if self.inst is not None and self.inst.status_code == 200:
            if (
                "text/xml" in self.inst.headers["Content-type"]
                or wd.webservice_content_type == 1
            ):
                self.result = ET.fromstring(self.inst.text)
                return True
            elif (
                "application/json" in self.inst.headers["Content-type"]
                or wd.webservice_content_type == 2
            ):
                try:
                    self.result = self.inst.json()
                    self.log_error_2_count = 0
                    return True
                except JSONDecodeError:
                    if not self.log_error_2_count:
                        logger.debug(f"{wd.url} - JSONDecodeError : {res.text}")
                    self.log_error_2_count += 1
        elif self.inst is not None:
            if not self.log_error_2_count:
                logger.debug(f"{wd.url} - status code = {res.status_code}")
            logger.debug(f"{wd.url} - status code = {res.status_code}")
            self.log_error_2_count += 1
        else:
            if not self.log_error_2_count:
                logger.debug(f"{wd.url} - get request is None")
            logger.debug(f"{wd.url} - get request is None")
            self.log_error_2_count += 1

        return False

    def after_read(self):
        self.result = None
        return super().after_read()

    def write_data(self, variable_id, value, task):
        if task.variable is None:
            return None
        wv = task.variable.webservicevariable
        wd = task.variable.device.webservicedevice
        path = wd.url
        for var in self._variables.values():
            if var.query_prev_value():
                if var.scaling is not None:
                    var.prev_value = var.scaling.scale_output_value(var.prev_value)
                path = path.replace(f"${var.id}", str(var.prev_value))
            else:
                logger.debug(
                    f"Cannot write to device {self._device} because variable {var} has no previous value"
                )
                return False
        try:
            res = requests.get(path, timeout=self.timeout)
        except:
            res = None
        if res is not None and res.status_code == 200:
            return True
        else:
            if res is None:
                logger.debug(f"Write to device {self._device} failed, response is None")
            else:
                logger.debug(
                    f"Write to device {self._device} error, response code is {res.status_code}"
                )
            return False
