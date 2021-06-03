# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import pyscada

__version__ = '0.7.0rc18'
__author__ = 'Camille Lavayssière'

default_app_config = 'pyscada.webservice.apps.PyScadaWebServiceConfig'

PROTOCOL_ID = 94

parent_process_list = [{'pk': PROTOCOL_ID,
                        'label': 'pyscada.webservice',
                        'process_class': 'pyscada.webservice.worker.Process',
                        'process_class_kwargs': '{"dt_set":30}',
                        'enabled': True}]
