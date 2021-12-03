# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from pyscada.visa.devices import GenericDevice
from pyscada.models import VariableProperty

from datetime import datetime
from math import floor
import requests
import json

import logging

logger = logging.getLogger(__name__)

"""Object based access to the Enedis API
Example::

    import sys
    sys.path.append(".")
    from enedis import ENEDIS
    TOKEN='your_token'
    ID='your_id'
    e=ENEDIS(headers={'Authorization':TOKEN}, payload={'usage_point_id':ID})
    r=e.send_post()
    print(r.status_code)
    prit(r.json())

"""
__author__ = "Camille Lavayssière"
__copyright__ = "Copyright 2021, Université de Pau et des Pays de l'Adour"
__credits__ = []
__license__ = "GPLv3"
__version__ = "0.1.0"
__maintainer__ = "Camille Lavayssière"
__email__ = "clavayssiere@univ-pau.fr"
__status__ = "Beta"
__docformat__ = 'reStructuredText'

from django.utils.timezone import now, make_aware, is_naive
import datetime
from time import sleep

class DataType(object):
    CONS_CURVE = "consumption_load_curve",  # Retourne les données de consommation par pas de 10, 30 ou 60 minutes (30 par défaut), pour chaque jour de la période demandée. La plage demandée ne peut excéder 7 jours et sur une période de moins de 24 mois et 15 jours avant la date d'appel.
    CONS_DAILY_MAX_POWER = "daily_consumption_max_power",  # Retourne la donnée maximale de consommation par pas de 1 jour, pour chaque jour de la période demandée. La plage demandée ne peut être que sur une période de moins de 36 mois et 15 jours avant la date d'appel.
    CONS_DAILY = "daily_consumption",  # Retourne les données de consommation par pas de 1 jour, pour chaque jour de la période demandée. La plage demandée ne peut être que sur une période de moins de 36 mois et 15 jours avant la date d'appel.
    PROD_CURVE = "production_load_curve",  # Retourne les données de production par pas de 10, 30 ou 60 minutes (30 par défaut), pour chaque jour de la période demandée. La plage demandée ne peut excéder 7 jours et sur une période de moins de 24 mois et 15 jours avant la date d'appel.
    PROD_DAILY = "daily_production",  # Retourne les données de production par pas de 1 jour, pour chaque jour de la période demandée. La plage demandée ne peut être que sur une période de moins de 36 mois et 15 jours avant la date d'appel.
    ID = "identity",  # Retourne l'identité du client
    CONTRACTS = "contracts",  # Retourne les données contractuelles
    ADDRESSES = "addresses"  # Retourne l'adresse du point de livraison et/ou production


class ENEDIS(object):

    def __init__(self, url=None, headers={}, payload={}, proxy_dict={}, timeout=10):
        self.headers = self.set_headers(headers)
        self.payload = self.set_payload(payload)
        self.url = self.set_url(url)
        self.proxy_dict = proxy_dict
        self.timeout = timeout

    def set_headers(self, headers={}):
        if 'Content-Type' not in headers:
            headers['Content-Type'] = 'application/json'
        if 'Authorization' not in headers:  # Jeton obtenu lors du consentement
            logger.warning('Authorization Token not set in headers')
        return headers

    def set_payload(self, payload={}):
        if 'type' not in payload:  # Le type de requête effectué
            payload['type'] = 'consumption_load_curve'
        if 'usage_point_id' not in payload:  # L'identifiant du point de livraison ou de production
            logger.warning('usage_point_id not set in payload')
        if 'start' not in payload:  # Date au format full-date de la RFC 3339, à savoir YYYY-MM-DD, à utiliser uniquement avec les requêtes consommation/production.
            payload['start'] = (datetime.date.today() + datetime.timedelta(days=-1)).isoformat()
        if 'end' not in payload:  # Date au format full-date de la RFC 3339, à savoir YYYY-MM-DD, à utiliser uniquement avec les requêtes consommation/production.
            payload['end'] = datetime.date.today().isoformat()
        return payload

    def set_url(self, url=None):
        if url is None:
            return "http://enedisgateway.tech/api"
        else:
            return url

    def send_post(self, url=None, proxy_dict={}):
        url = self.set_utl(url)
        if type(proxy_dict) == dict and len(proxy_dict):
            self.proxy_dict = proxy_dict
        try:
            r = requests.post(url, headers=self.headers, json=self.payload, proxies=self.proxy_dict, timeout=self.timeout)
        except Exception as e:
            logger.info(e)
        logger.debug(r.status_code)
        logger.debug(r.text)
        logger.debug(r.json())


class Handler(GenericDevice):
    """
    Enedis API and other API with the same command set
    """

    def connect(self, token, id, url=None):
        self.inst = ENEDIS(url=url, headers={'Authorization':str(token)}, payload={'usage_point_id':str(id)})

    def read_data_and_time(self, ws_action, device):
        """
        read values from the device
        """
        output = {}

        headers = self.webservices[ws_action_id]['object'].headers
        token = headers.get('Authorization', None)
        payload = self.webservices[ws_action_id]['object'].payload
        id = payload.get('usage_point_id', None)
        self.connect(token, id)

        if self.inst is None:
            return output

        for var_id in self.webservices[ws_action_id]['variables']:
            if self.inst.payload['type'] == DataType.CONS_CURVE:
                url = self.webservices[ws_action_id]['variables'][var_id]['object'].device.get('webservicedevice').get('url')
                proxy_dict = self.webservices[ws_action_id]['variables'][var_id]['object'].device.get('webservicedevice').get('proxy_dict')
                if type(proxy_dict) != dict:
                    proxy_dict = {
                                     "http": proxy_dict,
                                     "https": proxy_dict,
                                     "ftp": proxy_dict,
                                 }
                r = self.inst.send_post(url, proxy_dict)
                if r.status_code == requests.codes.ok:
                    interval_reading = r.json().get('meter_reading', {}).get('interval_reading', {})
                    for point in interval_reading:
                        try:
                            output[var_id] = (point.get('value', None), datetime.datetime.fromisoformat(point.get('date', None)))
                        except Exception as e:
                            logger.info(e)

        return output
