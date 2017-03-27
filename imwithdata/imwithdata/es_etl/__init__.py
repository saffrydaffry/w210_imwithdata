import csv
import os
from datetime import datetime

import boto3
from tqdm import tqdm

from imwithdata.es_etl.issues_actions import (
    issues,
    actions
)

bucket = "mids-capstone-rzst"
session = boto3.Session(profile_name="berkeley")
s3 = session.client("s3", "us-west-2")


class TwitterQueryAction(object):
    def __init__(self, es,
                 date=None):
        self.issue = None                          # Gets defined within the query runs
        self.action=None
        self.firstline = True
        self.key_prefix = "es_staging"              # add date of index before upload
        self.line_count = 0
        self.es = es
        self.date = date                            # given date of index being queried
        self.idx_date = None                        # if no date given, set this variable
        self.outfile = "es_data.csv"
        self.buffer = open(self.outfile, "w")
        self.querytimestamp = datetime.now().isoformat()


    @property
    def query(self):
        return 'message: "' + '" OR "'.join(actions[self.action]) + '"'

    @property
    def s3_loc(self):
        self.key_prefix = "/".join([self.key_prefix, self.date if self.date else self.idx_date])
        return "/".join([self.key_prefix, self.outfile])

    def _write_tweets(self, results):
        if self.firstline:
            self.firstline = False
            # TODO: Modify and add sections to match
            # rzst_events table in Drupal MySQL backend.
            fieldnames = ['issue',
                          'action',
                          'id',
                          'es_score',
                          'tweet_timestamp',
                          'query_timestamp',
                          'tweet_user',
                          'tweet'
                          ]
            self.writer = csv.DictWriter(self.buffer,
                                         fieldnames=fieldnames
                                         )
            self.writer.writeheader()
        n_results = len(results['hits']['hits'])
        if n_results > 0:
            print("Writing %s results.\n" % n_results)
            for result in tqdm(results['hits']['hits']):
                tweet = ""
                try:
                    tweet = result['_source']['message']
                except KeyError:
                    tweet = result['_source']['text']
                    
                row = {'issue': self.issue,
                       'action': self.action,
                       'id': result['_id'],
                       'es_score': result['_score'],
                       'tweet_timestamp': result['_source']['@timestamp'],
                       'query_timestamp': self.querytimestamp,
                       'tweet_user': result['_source']['user'],
                       # TODO: Ross can filter 'message' section of document
                       # parse this bit to pull out address/phone number
                       'tweet': tweet
                       }

                # skip retweets
                if row['tweet'][:2] == "RT":
                    continue
                self.writer.writerow(row)
                self.line_count += 1
        else:
            print("No results to save!")
            return None

    def run(self, action_key):
        self.action = action_key
        indices = [index for index in self.es.indices.get_alias().keys() if "-" in index]

        # if a date is given, only query that date's indices
        if self.date:
            indices = [index for index in indices if self.date in index]

        for index_ in indices:
            # find the issue
            self.issue = index_.split("-")[0]
            print("Running queries for issue: %s" % self.issue)

            if not self.date:
                self.idx_date = index_.split("-")[1]
                print("Appending date {idx_date_} to key".format(idx_date_=self.idx_date))
                self.key_prefix = "/".join([self.key_prefix, self.idx_date])

            print("Querying index %s" % index_)
            print(self.query)
            results = self.es.search(index=index_,
                                     q=self.query,
                                     size=10000,     # have to manually set this, default is 10
                                     request_timeout=30)
            self._write_tweets(results)

    def stop(self):
        self.buffer.close()
        print("Uploading {line_count} results to s3://{bucket}/{s3_loc}".format(line_count=self.line_count,
                                                                                bucket=bucket,
                                                                                s3_loc=self.s3_loc
                                                                                )
             )
        s3.upload_file(self.outfile, bucket, "/".join([self.s3_loc
                                                       ])
                       )
        print("Removing local temp file %s" % self.outfile)
        os.remove(self.outfile)
