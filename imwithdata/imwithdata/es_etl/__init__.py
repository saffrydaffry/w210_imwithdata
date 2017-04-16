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
        self.action = None
        self.tweets_firstline = True
        self.meetup_firstline = True
        self.key_prefix = "es_staging"              # add date of index before upload
        self.line_count = dict.fromkeys(['meetup', 'twitter'], 0.0)
        self.es = es
        self.date = date                            # given date of index being queried
        self.outfile = "es_data.csv"
        self.querytimestamp = datetime.now().isoformat()
        self.FIRST_MATCH = first_match
        self.doc_type = None

    @property
    def query(self):
        return 'message: "' + '" OR "'.join(actions[self.action]) + '"'

    def s3_loc(self, doc_type="twitter"):
        return "/".join([self.key_prefix, self.date, doc_type, self.outfile])

    def _write_meetup(self, results):
        # a little cheat with pandas since we
        # can assume the meetup data will be small
        from pandas.io.json import json_normalize

        meetup_file = "meetup"+ "_" + self.outfile
        # iterate through each tweet
        n_results = len(results['hits']['hits'])
        if n_results > 0:
            data = []
            print("Writing %s meetup results.\n" % n_results)
            for result in tqdm(results['hits']['hits']):
                data.append(result)

            df = json_normalize(data)
            df.drop_duplicates(inplace=True,
                               subset="_source.id"
                               )
            counts = df.shape[0]
            if self.meetup_firstline:
                self.meetup_firstline = False
                df.to_csv(meetup_file,
                          index=False)
            else:
                df.to_csv(meetup_file,
                          mode='a',
                          header=False,
                          index=False)
            self.line_count['meetup'] += counts

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
                       'tweet'
                       ]
        if self.tweets_firstline:
            self.tweets_firstline = False
            buffer = open("twitter_" + self.outfile, "w")
            # rzst_events table in Drupal MySQL backend.
            self.writer = csv.DictWriter(buffer,
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
                phone_numbers = []
                phone_matches = phonenumbers.PhoneNumberMatcher(tweet, "US")
                while phone_matches.has_next():
                    number = phone_matches.next()
                    number = phonenumbers.format_number(number.number,
                                                        phonenumbers.PhoneNumberFormat.NATIONAL
                                                        )
                    phone_numbers.append(number)
                phone_numbers = '; '.join(phone_numbers)
                        
                # -- States -- #
                states = ''
                tweet_states = re.findall(state_regex, tweet)
                if tweet_states:
                    tweet_states = list(set(tweet_states))
                    states = '; '.join(tweet_states)
                
                # -- CITIES -- #
                cities = ''
                tweet_cities = re.findall(city_regex, tweet)
                if tweet_cities:
                    tweet_cities = list(set([city.title() for city in tweet_cities]))
                    cities = '; '.join(tweet_cities)
                
                # -- URLS -- #
                urls = ''
                tweet_urls = re.findall(web_url_regex, tweet)
                if tweet_urls:
                    tweet_urls = list(set(tweet_urls))
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
                tweet_legislators = re.findall(leg_name_regex, tweet)
                tweet_legislators = list(set(tweet_legislators))
                if tweet_legislators:
                    if len(tweet_legislators) == 1:
                        leg_names = tweet_legislators[0]
                    else:
                        leg_names = '; '.join(tweet_legislators)

                # -- LEGISLATOR TWITTER HANDLES -- #
                leg_twitter_handles = ''
                tweet_leg_handles = re.findall(leg_twitter_regex, tweet)
                tweet_leg_handles = list(set(tweet_leg_handles))
                if tweet_leg_handles:
                    #if len(tweet_leg_handles) == 1:
                    #    leg_twitter_handles = tweet_leg_handles[0]
                    #else:
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
                    temp_row = {key: value for key, value in temp_row.items()}


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
                self.line_count['twitter'] += 1
        else:
            print("No results to save!")
            return None

    def run(self, action_key):
        self.action = action_key
        indices = [index for index in self.es.indices.get_alias().keys() if "-" in index]
        doc_types = {
            'twitter':
                {
                    'list': [
                        'twitter',
                        'immigrants',
                        'worker',
                        'climate',
                        'voting',
                        'lgbt',
                        'womens_right',
                        'speech',
                        'healthcare'
                    ],
                    'func': self._write_tweets
                },
            'meetup': {
                    'list': ['meetup'],
                    'func': self._write_meetup
                }
        }
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
            if "meetup" in self.issue:
                print("Extracting meetup data.")
                results = self.es.search(index=index_,
                                         q=self.query,
                                         size=10000,     # have to manually set this, default is 10
                                         request_timeout=30)
                self._write_meetup(results)

            else:
                for doc_type in doc_types.keys():
                    print("Querying type %s" % doc_type)
                    self.doc_type = doc_type
                    results = self.es.search(index=index_,
                                             doc_type=doc_types[doc_type]['list'],
                                             q=self.query,
                                             size=10000,     # have to manually set this, default is 10
                                             request_timeout=30)
                    doc_types[doc_type]['func'](results)
                    #self._write_tweets(results)

    def stop(self):
        for doc_type in ['twitter', 'meetup']:
            upload_key = self.s3_loc(doc_type)
            file = "_".join([doc_type, self.outfile])
            if os.path.isfile(file):
                print("""Uploading {line_count} {type} results to 
                s3://{bucket}/{s3_loc}
                """.format(line_count=self.line_count[doc_type],
                           type=doc_type,
                           bucket=bucket,
                           s3_loc=upload_key
                           )
                      )
                s3.upload_file(file, bucket, upload_key)
                response = s3.put_object_acl(ACL='public-read', Bucket='mids-capstone-rzst',
                                             Key=upload_key)['ResponseMetadata']
                if response['HTTPStatusCode'] == 200:
                    print("Successfully set permissions to public-read")
                else:
                    print("Failed to set permissions for %s" % upload_key)

                print("Removing local temp file %s" % file)
                os.remove(file)
