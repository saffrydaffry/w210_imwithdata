import csv
import os
import re
import phonenumbers
from datetime import datetime
import spacy

import boto3
from tqdm import tqdm

from imwithdata.es_etl.issues_actions import (
    issues,
    actions,
    state_regex,
    city_regex,
    web_url_regex,
    date_include_regex,
    date_exclude_regex,
    leg_name_regex,
    leg_twitter_regex
)
from imwithdata.utils import get_ini_vals
# Configs form .ini file
# .ini location
config_file = os.path.join(os.pardir,
                           'config',
                           'config.ini'
                           )

aws_creds = get_ini_vals(config_file, 'aws.creds')
bucket = "mids-capstone-rzst"
s3 = boto3.client("s3", "us-west-2",
                  aws_access_key_id=aws_creds['AWS_ACCESS_KEY_ID'],
                  aws_secret_access_key=aws_creds['AWS_SECRET_ACCESS_KEY']
                  )

nlp = spacy.load('en')

class ElasticSearchQueryETL(object):
    def __init__(self, es,
                 date=None,
                 first_match=True):
        self.issue = None                          # Gets defined within the query runs
        self.action=None
        self.firstline = True
        self.key_prefix = "es_staging"              # add date of index before upload
        self.line_count = 0
        self.es = es
        self.date = date                            # given date of index being queried
        self.outfile = "es_data.csv"
        self.buffer = open(self.outfile, "w")
        self.querytimestamp = datetime.now().isoformat()
        self.FIRST_MATCH = first_match

    @property
    def query(self):
        return 'message: "' + '" OR "'.join(actions[self.action]) + '"'

    @property
    def s3_loc(self):
        self.key_prefix = "/".join([self.key_prefix, self.date])
        return "/".join([self.key_prefix, self.outfile])

    def _write_tweets(self, results):
        fieldnames_ = ['issue',
                       'action',
                       'id',
                       'es_score',
                       'tweet_timestamp',
                       'query_timestamp',
                       'tweet_user',
                       'tweet_cities',
                       'tweet_states',
                       'tweet_urls',
                       'tweet_phone_numbers',
                       'tweet_dates_ref',
                       'tweet_legislator_names',
                       'tweet_legislator_handles',
                       # TODO: Ross to filter 'message' section of document for address
                       'tweet'
                       ]
        if self.firstline:
            self.firstline = False
            # TODO: Modify and add sections to match
            # rzst_events table in Drupal MySQL backend.
            self.writer = csv.DictWriter(self.buffer,
                                         fieldnames=fieldnames_
                                         )
            self.writer.writeheader()

        # instantiate the row to be written as empty dict
        row = dict.fromkeys(fieldnames_, "")

        # iterate through each tweet
        n_results = len(results['hits']['hits'])
        if n_results > 0:
            print("Writing %s results.\n" % n_results)
            for result in tqdm(results['hits']['hits']):
                tweet = ""

                # potential for two KeyErrors, the second won't be caught
                # so use if statement instead.
                if 'message' in result['_source'].keys():
                    tweet = result['_source']['message']
                elif 'text' in result['_source'].keys():
                    tweet = result['_source']['text']
                else:
                    print("issue with document {id}".format(id=result['_id']))
                    print("From index {issue}-{date}".format(issue=self.issue,
                                                             date=self.date))
                    print(result['_source'])
                    # skip meetup for now
                    continue
                # EXTRACT PHONE NUMBER, URL, STATE, CITY, DATE, LEGISLATOR NAMES, AND LEGISLATOR TWITTER HANDLES #
                # -- Phone Numbers -- #
                phone_numbers = ''
                phone_matches = phonenumbers.PhoneNumberMatcher(tweet, "US")
                if phone_matches:
                    phone_matches = list(set(phone_matches))
                    if len(phone_matches) == 1:  
                        phone_numbers = phonenumbers.format_number(match.number,phonenumbers.PhoneNumberFormat.NATIONAL)
                    elif len(phone_matches) > 1:
                        phone_numbers = '; '.join(matches)
                        
                # -- States -- #
                states = ''
                tweet_states = re.findall(state_regex,tweet)
                if tweet_states:
                    tweet_states = list(set(tweet_states))
                    if len(tweet_states) == 1:
                        states = tweet_states
                    else:
                        states = '; '.join(tweet_states)
                
                # -- CITIES -- #
                cities = ''
                tweet_cities = re.findall(city_regex,tweet)
                if tweet_cities:
                    tweet_cities = list(set([city.title() for city in tweet_cities]))
                    if len(tweet_cities) == 1:
                        cities = tweet_cities[0]
                    else:
                        cities = '; '.join(tweet_cities)
                
                # -- URLS -- #
                urls = ''
                tweet_urls = re.findall(web_url_regex,tweet)
                if tweet_urls:
                    tweet_urls = list(set(tweet_urls))
                if len(tweet_urls) == 1:
                    urls = tweet_urls[0]
                else:
                    urls = '; '.join(tweet_urls)

                # -- DATES -- #
                dates = ''
                doc = nlp(tweet)
                all_dates = [doc.text for doc in doc.ents if doc.label_ == 'DATE']
                date_matches = re.findall(date_include_regex, ' '.join(all_dates))
                ### EXCLUDE SOME DIRTY DATES FROM TWITTER THAT SPACY MISTAKENLY INCLUDES    
                if date_matches:
                    dates = all_dates[0]
                        #re.findall(date_exclude_regex,ent.text)
                        

                # -- LEGISLATOR NAMES -- #
                leg_names = ''
                tweet_legislators = re.findall(leg_name_regex,tweet)
                tweet_legislators = list(set(tweet_legislators))
                if tweet_legislators:
                    if len(tweet_legislators) == 1:
                        leg_names = tweet_legislators[0]
                    else:
                        leg_names = '; '.join(tweet_legislators)

                # -- LEGISLATOR TWITTER HANDLES -- #
                leg_twitter_handles = ''
                tweet_leg_handles = re.findall(leg_twitter_regex,tweet)
                tweet_leg_handles = list(set(tweet_leg_handles))
                if tweet_leg_handles:
                    if len(tweet_leg_handles) == 1:
                        leg_twitter_handles = tweet_leg_handles[0]
                else:
                    leg_twitter_handles = '; '.join(tweet_leg_handles)

                # process if only first item is needed
                temp_row = {'tweet_cities': cities,
                            'tweet_states': states,
                            'tweet_urls': urls,
                            'tweet_phone_numbers': phone_numbers,
                            'tweet_dates_ref': dates,
                            'tweet_legislator_names': leg_names,
                            'tweet_legislator_handles': leg_twitter_handles
                            }

                if self.FIRST_MATCH:
                    temp_row = {key: (value[0] if len(value) > 0 else value)
                                for key, value in temp_row.items()}


                # fill in the values to row
                row.update({'issue': self.issue,
                           'action': self.action,
                           'id': result['_id'],
                           'es_score': result['_score'],
                           'tweet_timestamp': result['_source']['@timestamp'],
                           'query_timestamp': self.querytimestamp,
                           'tweet_user': result['_source']['user'],
                           # TODO: Ross to filter 'message' section of document for address
                           'tweet': tweet
                       })
                row.update(temp_row)

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
                self.date = self.querytimestamp

            print("Querying index %s" % index_)
            print(self.query)
            results = self.es.search(index=index_,
                                     q=self.query,
                                     size=10000,     # have to manually set this, default is 10
                                     request_timeout=30)
            self._write_tweets(results)

    def stop(self):
        self.buffer.close()
        upload_key = self.s3_loc
        print("Uploading {line_count} results to s3://{bucket}/{s3_loc}".format(line_count=self.line_count,
                                                                                bucket=bucket,
                                                                                s3_loc=upload_key
                                                                                )
              )
        s3.upload_file(self.outfile, bucket, upload_key)
        response = s3.put_object_acl(ACL='public-read', Bucket='mids-capstone-rzst',Key=upload_key)['ResponseMetadata']
        if response['HTTPStatusCode'] == 200:
            print("Successfully set permissions to public-read")
        else:
            print("Failed to set permissions for %s" % upload_key)

        print("Removing local temp file %s" % self.outfile)
        os.remove(self.outfile)
