# -*- coding: utf-8 -*-
from __future__ import unicode_literals

__version__ = "0.8.0"
__author__ = "Camille Lavayssiere"
__email__ = "team@pyscada.org"
__description__ = "WebService extension for PyScada a Python and Django based Open Source SCADA System"
__app_name__ = "WebService"

PROTOCOL_ID = 94

parent_process_list = [{'pk': PROTOCOL_ID,
                        'label': 'pyscada.' + __app_name__.lower(),
                        'process_class': 'pyscada.' + __app_name__.lower() + '.worker.Process',
                        'process_class_kwargs': '{"dt_set":30}',
                        'enabled': True}]
