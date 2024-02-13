# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from pyscada.models import Variable

from dateutil.relativedelta import relativedelta
import os
from datetime import datetime, date, timedelta
import requests
import json
from pytz import utc

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
        self.params = {}

    def set_url(self, url=None):
        if url is None:
            return "https://www.infoclimat.fr/opendata/"
        else:
            return url

    def set_params(self, station, token, start_date, end_date):
        self.params = {
            "method": "get",
            "format": "json",
            "stations[]": station,
            "token": token,
            "start": start_date,
            "end": end_date,
        }

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

    def read_data_all(self, variables_dict):
        wd = self._device.webservicedevice
        payload = json.loads(wd.payload)
        logger.info(self._variables)
        hourly_variables = {}
        classic_variables = {}
        for v in self._variables:
            if "hourly" in self._variables[v].webservicevariable.path:
                hourly_variables[v] = self._variables[v]
            else:
                classic_variables[v] = self._variables[v]

        # read non hourly variables
        output = super().read_data_all(classic_variables, erase_cache=True)


        last_timestamp = Variable.objects.get_last_element_timestamp(
            variables=hourly_variables.values()
        )
        logger.info(f"last_timestamp : {last_timestamp}")
        months_offset_max = 36
        t_from = date.fromtimestamp(
            self._get_min_time(months_offset_max, last_timestamp)
        )
        logger.info(f"t_from : {t_from}")
        logger.info(f"Starting to read from {t_from.isoformat()}")
        stop = False

        while not stop:
            t_to = t_from + timedelta(days=6)
            if t_to >= date.today():
                stop = True
                t_to = date.today()
            payload["start"] = t_from.isoformat()
            payload["end"] = t_to.isoformat()
            try:
                wd.payload = json.dumps(payload)
            except json.decoder.JSONDecodeError as e:
                logger.info(f"Device {self._device} - JSONDecodeError : {e}")
                break

            for i in range(0, 3):
                # try 3 times max
                logger.info(
                    f"{wd} from {t_from.isoformat()} to {t_to.isoformat()} iteration {i}"
                )
                out = super().read_data_all(hourly_variables, erase_cache=False)
                if len(out):
                    for var in out:
                        if var not in output:
                            logger.info(f"adding {var} to output")
                            output.append(var)
                    break
            t_from = t_to
        return output

    def read_data_and_time(self, variable_instance):
        wv = variable_instance.webservicevariable
        if self.result is None:
            return None, None

        if wv.path.split()[0] == "hourly":
            values = []
            read_times = []
            tmp = self.result
            tmp = tmp.get(wv.path.split()[0], {})
            tmp = tmp.get(wv.path.split()[1], {})
            for i in tmp:
                value = i.get(wv.path.split()[-1], None)
                read_time = i.get("dh_utc", None)
                if read_time is None:
                    continue
                read_time = datetime.fromisoformat(read_time).astimezone(utc)
                read_time = read_time.timestamp()
                values.append(value)
                read_times.append(read_time)
            logger.info(f"{len(values)}")
            return values, read_times
        else:
            return super().read_data_and_time(variable_instance)

    def _get_min_time(self, months_offset_max=36, time_min=None):
        if time_min is None:
            time_min = (
                datetime.today()
                - relativedelta(months=months_offset_max)
                + relativedelta(days=1)
            ).timestamp()
        logger.info(f"time_min : {time_min}")
        return time_min
