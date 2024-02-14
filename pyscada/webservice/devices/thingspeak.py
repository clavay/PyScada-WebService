# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from pyscada.models import Variable
from pyscada.webservice.devices import GenericDevice

from dateutil.relativedelta import relativedelta
import os
from datetime import datetime, date, timedelta
import requests
import json
from pytz import utc

import logging

logger = logging.getLogger(__name__)


class Handler(GenericDevice):
    """
    Thingspeak API and other API with the same command set
    examples:
    device url:
    - https://api.thingspeak.com/channels/2409726/feeds.json
    variable path: (when starting with "feeds" it will get all the result using the "created_at" for the timestamp)
    - channel name
    - feeds field1
    """

    def read_data_and_time(self, variable_instance):
        wv = variable_instance.webservicevariable
        if self.result is None:
            return None, None

        if wv.path.split()[0] == "feeds":
            values = []
            read_times = []
            tmp = self.result
            tmp = tmp.get(wv.path.split()[0], {})
            for i in tmp:
                value = i.get(wv.path.split()[-1], None)
                read_time = i.get("created_at", None)
                if read_time is None:
                    continue
                read_time = datetime.fromisoformat(read_time)
                read_time = read_time.timestamp()
                values.append(value)
                read_times.append(read_time)
            logger.info(f"{len(values)}")
            return values, read_times
        else:
            return super().read_data_and_time(variable_instance)
