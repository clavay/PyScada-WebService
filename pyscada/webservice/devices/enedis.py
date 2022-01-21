# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import os
import datetime
import requests
import json

import logging

logger = logging.getLogger(__name__)

if os.getenv('DJANGO_SETTINGS_MODULE') is not None:
    from pyscada.webservice.devices import GenericDevice
else:
    import sys
    logger.debug("Django settings not configured.")
    GenericDevice = object
    logging.basicConfig(
        level=logging.DEBUG,
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )

"""Object based access to the Enedis API
Example:

import sys
sys.path.append(".")
from enedis import ENEDIS, DataType
TOKEN='your_token'
ID='your_id'
e=ENEDIS(headers={'Authorization':TOKEN}, payload={'usage_point_id':ID})
r=e.send_post()
print(r.status_code)
print(r.json())

# Other Example:
print(DataType.__dict__)
e=ENEDIS(headers={'Authorization':TOKEN}, payload={'type':DataType.PROD_DAILY,'usage_point_id':ID, 'start':'2022-01-01', 'end':'2022-01-05'})
r=e.send_post()
print(r.status_code)
print(r.json())
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


class DataType(object):
    """
    CONS_CURVE  # Retourne les données de consommation par pas de 10, 30 ou 60 minutes (30 par défaut), pour chaque jour de la période demandée. La plage demandée ne peut excéder 7 jours et sur une période de moins de 24 mois et 15 jours avant la date d'appel.
    CONS_DAILY_MAX_POWER  # Retourne la donnée maximale de consommation par pas de 1 jour, pour chaque jour de la période demandée. La plage demandée ne peut être que sur une période de moins de 36 mois et 15 jours avant la date d'appel.
    CONS_DAILY  # Retourne les données de consommation par pas de 1 jour, pour chaque jour de la période demandée. La plage demandée ne peut être que sur une période de moins de 36 mois et 15 jours avant la date d'appel.
    PROD_CURVE  # Retourne les données de production par pas de 10, 30 ou 60 minutes (30 par défaut), pour chaque jour de la période demandée. La plage demandée ne peut excéder 7 jours et sur une période de moins de 24 mois et 15 jours avant la date d'appel.
    PROD_DAILY  # Retourne les données de production par pas de 1 jour, pour chaque jour de la période demandée. La plage demandée ne peut être que sur une période de moins de 36 mois et 15 jours avant la date d'appel.
    ID  # Retourne l'identité du client
    CONTRACTS  # Retourne les données contractuelles
    ADDRESSES  # Retourne l'adresse du point de livraison et/ou production
    """

    CONS_CURVE = "consumption_load_curve"  # Retourne les données de consommation par pas de 10, 30 ou 60 minutes (30 par défaut), pour chaque jour de la période demandée. La plage demandée ne peut excéder 7 jours et sur une période de moins de 24 mois et 15 jours avant la date d'appel.
    CONS_DAILY_MAX_POWER = "daily_consumption_max_power"  # Retourne la donnée maximale de consommation par pas de 1 jour, pour chaque jour de la période demandée. La plage demandée ne peut être que sur une période de moins de 36 mois et 15 jours avant la date d'appel.
    CONS_DAILY = "daily_consumption"  # Retourne les données de consommation par pas de 1 jour, pour chaque jour de la période demandée. La plage demandée ne peut être que sur une période de moins de 36 mois et 15 jours avant la date d'appel.
    PROD_CURVE = "production_load_curve"  # Retourne les données de production par pas de 10, 30 ou 60 minutes (30 par défaut), pour chaque jour de la période demandée. La plage demandée ne peut excéder 7 jours et sur une période de moins de 24 mois et 15 jours avant la date d'appel.
    PROD_DAILY = "daily_production"  # Retourne les données de production par pas de 1 jour, pour chaque jour de la période demandée. La plage demandée ne peut être que sur une période de moins de 36 mois et 15 jours avant la date d'appel.
    ID = "identity"  # Retourne l'identité du client
    CONTRACTS = "contracts"  # Retourne les données contractuelles
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
            return "https://enedisgateway.tech/api"
        else:
            return url

    def send_post(self, url=None, proxy_dict={}):
        url = self.set_url(url)
        if type(proxy_dict) == dict and len(proxy_dict):
            self.proxy_dict = proxy_dict
        try:
            r = requests.post(url, headers=self.headers, json=self.payload, proxies=self.proxy_dict, timeout=self.timeout)
            return r
        except Exception as e:
            logger.info(e)


class Handler(GenericDevice):
    """
    Enedis API and other API with the same command set
    """

    def connect(self, token, id, url=None):
        self.inst = ENEDIS(url=url, headers={'Authorization':str(token)}, payload={'usage_point_id':str(id)})

    def read_data_and_time(self, ws_action_id, device):
        """
        read values from the device
        """
        output = {}

        try:
            headers = device.webservices[ws_action_id]['object'].headers
            payload = device.webservices[ws_action_id]['object'].payload
            token = json.loads(headers).get('Authorization', None)
            id = json.loads(payload).get('usage_point_id', None)
        except json.decoder.JSONDecodeError as e:
            logger.debug(e)
            logger.debug(headers)
            logger.debug(payload)
            return output
        self.connect(token, id)

        if self.inst is None:
            logger.debug("inst is None")
            return output

        for var_id in device.webservices[ws_action_id]['variables']:
            #logger.debug(var_id)
            if self.inst.payload['type'] == DataType.CONS_CURVE:
                url = getattr(getattr(device.webservices[ws_action_id]['variables'][var_id]['object'].device, 'webservicedevice'), 'url')
                proxy_dict = getattr(getattr(device.webservices[ws_action_id]['variables'][var_id]['object'].device, 'webservicedevice'), 'http_proxy')
                if type(proxy_dict) != dict:
                    proxy_dict = {
                                     "http": proxy_dict,
                                     "https": proxy_dict,
                                     "ftp": proxy_dict,
                                 }
                r = self.inst.send_post(url, proxy_dict)
                #logger.debug(r)
                if r is not None and r.status_code == requests.codes.ok:
                    interval_reading = r.json().get('meter_reading', {}).get('interval_reading', {})
                    for point in interval_reading:
                        if var_id not in output:
                            output[var_id] = []
                        try:
                            value = point.get('value', None)
                            if value is not None:
                                value = float(value)
                            time = point.get('date', None)
                            if time is not None:
                                time = datetime.datetime.fromisoformat(time).timestamp()
                            if value is not None and time is not None:
                                output[var_id].append((value, time))
                        except Exception as e:
                            logger.info(e)
            else:
                logger.debug(self.inst.payload['type'])
                logger.debug(DataType.CONS_CURVE)


        return output
