#!/usr/bin/env python3
"""Grab data from ElasticSearch (Twitter-only For now).
Query Data, clean it, and put into RZST.US SQL Backend.


"""
import argparse
import os
from configparser import ConfigParser
from datetime import (
    datetime,
    timedelta
)

from elasticsearch import (
    Elasticsearch
)
from imwithdata.es_etl import ElasticSearchQueryETL
from imwithdata.es_etl.issues_actions import (
    issues,
    actions
)
from imwithdata.utils import get_ini_vals

# Configs form .ini file
# .ini location
config_file = os.path.join(os.pardir,
                           'config',
                           'config.ini'
                           )

# -- Configurations -- #
es_creds = get_ini_vals(config_file, 'elasticsearch')
mysql_creds = get_ini_vals(config_file, 'mysql')

# MySQL Event Table Fields
rzst_event_header =[
    'elasticsearch_id',
    'title',
    'body_value',
    'location_text',
    'event_datetime_from',
    'event_datetime_to',
    'score',
    'insert_dt',
    'event_type',
    'pri_action_type',
    'sec_action_type'
]

# Global Constants
format = "%y.%m.%d"

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--date', default=(datetime.now() - timedelta(days=1)).date().strftime(format=format),
                        type=str,
                        help="""The date to query data from. Query all indices, if == 'all'."
                            Date has to be in yy.mm.dd format.
                           """
                       )
    args = parser.parse_args()

    q_date = args.date


    try:
        datetime.strptime(q_date, format)
        print("Uploading indices created on %s" % q_date)
    except ValueError:
        parser.print_help()

    try:
        es = Elasticsearch(
            [es_creds['host']],
            http_auth=('', ''),
            port=es_creds['port'],
            use_ssl=False
        )
        print(es.info())
        print("List of available indices:")
        es_indices = es.indices.get_alias().keys()
        print(es_indices)

    except ConnectionError:
        raise("Failed to Connect to ElasticSearch on {hostname}".format(hostname=es_creds['host']))

    eq = ElasticSearchQueryETL(es, date=q_date)

    for action in actions.keys():
        eq.run(action)
    eq.stop()


if __name__ == "__main__":
    main()
