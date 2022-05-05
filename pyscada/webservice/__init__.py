# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import pyscada

__version__ = '0.7.1rc1'
__author__ = 'Camille Lavayssière'

PROTOCOL_ID = 94

parent_process_list = [{'pk': PROTOCOL_ID,
                        'label': 'pyscada.webservice',
                        'process_class': 'pyscada.webservice.worker.Process',
                        'process_class_kwargs': '{"dt_set":30}',
                        'enabled': True}]