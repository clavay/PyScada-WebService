# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from pyscada.models import Variable

from dateutil.relativedelta import relativedelta
import os
from datetime import datetime, date, timedelta
import requests
import json

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

"""Object based access to infoclimat
https://www.infoclimat.fr/opendata/?method=get&format=json&stations[]=000PS&start=2024-01-01&end=2024-01-08&token=XXX

import sys
sys.path.append(".")
from infoclimat import infoclimat
TOKEN=''
station='000PS'
start_date='2024-01-01'
end_date='2024-01-08'
e=infoclimat()
e.set_params(station,TOKEN,start_date,end_date)
r=e.send_get()
print(r.status_code)
print(r.json())

"""

__author__ = "Benoît Larroque"
__copyright__ = "Copyright 2024, Université de Pau et des Pays de l'Adour"
__credits__ = []
__license__ = "AGPLv3"
__version__ = "0.1.0"
__maintainer__ = "Benoît Larroque"
__email__ = "blarroq1@univ-pau.fr"
__status__ = "Beta"
__docformat__ = "reStructuredText"



class infoclimat(object):
    def __init__(self, url=None, headers={}, payload={}, proxy_dict={}, timeout=10):
        self.url = self.set_url(url)
        self.proxy_dict = proxy_dict
        self.timeout = timeout
        self.params={}

    def set_url(self, url=None):
        if url is None:
            return "https://www.infoclimat.fr/opendata/"
        else:
            return url
    def set_params(self, station, token, start_date, end_date):
        self.params= {"method":"get","format":"json","stations[]":station,"token":token, "start":start_date, "end":end_date}

    def send_get(self):
        try:
            r = requests.get(
                self.url,
                params=self.params,
                timeout=self.timeout,
            )
            return r
        except Exception as e:
            logger.info(e)


class Handler(GenericDevice):
    """
    Infoclimat API and other API with the same command set
    """

    def connect(self):
        self.inst = infoclimat()
        return True

    def _get_min_time(
        self, months_offset_max=36, time_min= None
    ):
        if time_min is None:
            time_min = (
                datetime.today()
                - relativedelta(months=months_offset_max)
                + relativedelta(days=1)
            ).timestamp()
        logger.info(f"time_min : {time_min}")
        return time_min


    def read_data_all(self, variables_dict):
        output = []

        if self.before_read():
            variables_values = {}
            variables_timestamps = {}
            for wsa_id in self.webservices:
                headers = self.webservices[wsa_id]['object'].headers
                token = json.loads(headers).get('token', None)
                station = json.loads(headers).get('station', None)
                if station is None or token is None:
                    logger.warning(f"Need a token and a station : {token} {station}")
                    continue

                # erase variable cached values
                variables = []
                for var_id in self.webservices[wsa_id]["variables"]:
                    variables_dict[var_id]["object"].update_values([], [], erase_cache=True)
                    variables.append(variables_dict[var_id]["object"])
                logger.info(variables)
                last_timestamp = Variable.objects.get_last_element_timestamp(variables=variables)
                logger.info(f"last_timestamp : {last_timestamp}")
                months_offset_max = 2
                t_from = date.fromtimestamp(
                    self._get_min_time(
                        months_offset_max, last_timestamp
                    )
                )
                logger.info(f"Starting to read from {t_from}")
                stop = False
                while not stop:
                    t_to = t_from + timedelta(days=6)
                    if t_to >= date.today():
                        stop = True
                        t_to = date.today()

                    for i in range(0, 3):
                        # try 3 times max
                        logger.info(f"ID:{wsa_id} from {t_from} to {t_to} iteration {i}")
                        try:
                            self.inst.set_params(station, token, t_from.isoformat(), t_to.isoformat())
                            r = self.inst.send_get()
                            if r is None:
                                continue
                        except TypeError:
                            pass
                        except Exception as e:
                            logger.warning(
                                f"Read failed {i} for {self._device} : {e}"
                            )
                            sleep(2)
                        else:
                            for var_id in self.webservices[wsa_id]["variables"]:
                                values = []
                                read_times = []
                                try:
                                    tmp = r.json()
                                except requests.exceptions.JSONDecodeError as e:
                                    logger.warning(f"JSON decode error for webservice action {wsa_id} variable {var_id} : {e}")
                                    continue
                                hourly_data = False
                                keys = self.webservices[wsa_id]["variables"][var_id]["variable_path"]
                                for key in keys.split():
                                    tmp = tmp.get(key, {})
                                    if hourly_data:
                                        break
                                    if key == "hourly":
                                        hourly_data = True
                                if hourly_data:
                                    for i in tmp:
                                        value = i.get(keys.split()[-1], None)
                                        read_time = i.get("dh_utc", None)
                                        if read_time is None:
                                            continue
                                        read_time = datetime.fromisoformat(read_time).timestamp()
                                        values.append(value)
                                        read_times.append(read_time)
                                    logger.info(f"{len(values)}")
                                if len(values):
                                    variables_dict[var_id]["object"].update_values(values, read_times, erase_cache=False)

                        break
                    t_from = t_to
                for var_id in self.webservices[wsa_id]["variables"]:
                    if len(variables_dict[var_id]["object"].cached_values_to_write):
                        output.append(variables_dict[var_id]["object"])
                logger.info(len(output))
            return output
