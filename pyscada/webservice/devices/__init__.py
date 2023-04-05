# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from .. import PROTOCOL_ID
from pyscada.device import GenericHandlerDevice

import logging

logger = logging.getLogger(__name__)

driver_ok = True


class GenericDevice(GenericHandlerDevice):
    def __init__(self, pyscada_device, variables):
        super().__init__(pyscada_device, variables)
        self.driver_ok = driver_ok
        self._protocol = PROTOCOL_ID
        self.last_value = None
        self.webservices = None

    def set_webservices(self, webservices):
        self.webservices = webservices

    def read_data(self, item):
        """
        read values from the device
        """
        output = {}

        self.inst = True

        res = self.webservices[item]['object'].request_data(self)
        for var in self.webservices[item]['variables']:
            path = self.webservices[item]['variables'][var]['device_path'] + self.webservices[item]['object'].path
            if self.webservices[item]['variables'][var]['value'] is not None and \
                    self.webservices[item]['object'].webservice_RW:
                logger.warning("Variable " + str(var) + " is in more than one WebService")
            try:
                if res[path]["content_type"] is None:
                    self._not_accessible_reason = "content type is None"
                    self.inst = None
                    self.webservices[item]['variables'][var]['value'] = None
                    break
                else:
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
                self._not_accessible_reason = f"content_type missing in {path} : {res[path]}"
                self.inst = None
                self.webservices[item]['variables'][var]['value'] = None
                break
            except TypeError as e:
                self._not_accessible_reason = e
                self.inst = None
                self.webservices[item]['variables'][var]['value'] = None
                break
            except AttributeError:
                self.inst = None
                self._not_accessible_reason = f"{path} : {self.webservices[item]['variables'][var]['variable_path']} not found in {res[path]['result']}"
                self.webservices[item]['variables'][var]['value'] = None
                break
            except SyntaxError:
                self.inst = None
                self._not_accessible_reason = f"{path} : {self.webservices[item]['variables'][var]['variable_path']} : XPath syntax error "
                self.webservices[item]['variables'][var]['value'] = None
                break

            output[var] = (self.webservices[item]['variables'][var]['value'], self.time())

        return output

    def read_data_and_time(self, ws_action_id):
        """
        read values and timestamps from the device
        """
        return self.read_data(ws_action_id)  # , self.time()

    def read_data_all(self, variables_dict):
        output = []

        self.before_read()
        for wsa_id in self.webservices:
            res = self.read_data_and_time(wsa_id)
            self.accessibility()
            for item_pk in res:
                item = self._variables[item_pk]['object']
                value, time = res[item_pk]
                try:
                    if value is not None and item.update_value(value, time):
                        output.append(item.create_recorded_data_element())
                except ValueError:
                    logger.debug(str(item) + " - value is : " + str(self.webservices[wsa_id]['variables'][item]['value']))
                    pass
                except TypeError:
                    logger.debug(str(item) + " - value is : " + str(self.webservices[wsa_id]['variables'][item]['value']))
                    pass
        self.after_read()
        return output
