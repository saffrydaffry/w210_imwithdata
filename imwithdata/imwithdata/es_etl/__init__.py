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
        self.outfile = "es_data.csv"
        self.buffer = open(self.outfile, "w")
        self.querytimestamp = datetime.now().isoformat()


    @property
    def query(self):
        return 'message: "' + '" OR "'.join(actions[self.action]) + '"'

    @property
    def s3_loc(self):
        self.key_prefix = "/".join([self.key_prefix, self.date])
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
                
                
                
                #### EXTRACT PHONE NUMBER, URL, STATE, CITY, DATE, LEGISLATOR NAMES, AND LEGISLATOR TWITTER HANDLES ####
                
                ### PHONE NUMBERS
                try:
                    phone_numbers= []
                    if phonenumbers.PhoneNumberMatcher(tweet, "US"):
                        for match in phonenumbers.PhoneNumberMatcher(tweet, "US"):
                                    phone_numbers.append(phonenumbers.format_number(match.number, 
                                                                                    phonenumbers.PhoneNumberFormat.NATIONAL))
                    ### IF WE DECIDE WE ONLY WANT ONE PHONE PER RECORD       
                    #if phone_numbers:
                        #phone_numbers = phone_numbers[0]
                        
                except:
                    phone_numbers = []
                    #print 'phone number error'
                    #print tweet
                
                
                ### STATES
                try:
                    states = []
                    if state_regex.match(tweet):
                        for match in re.findall(state_regex, tweet):
                            states.append(match)
                    
                    ### IF WE DECIDE WE ONLY WANT ONE STATE PER RECORD       
                    #if states:
                        #states = states[0]
                except:
                    states = []
                    #print 'state error'
                    #print tweet
                
                ### CITIES
                try:
                    cities = []
                    if city_regex.match(tweet):
                        for match in re.findall(city_regex, tweet):
                            if match != 'White House' and match != 'Liberal' and match != 'Perry' and match != 'Price':
                                cities.append(match)
                                
                    ### IF WE DECIDE WE ONLY WANT ONE CITY PER RECORD       
                    #if cities:
                        #cities = cities[0]
                except:
                    cities = []
                    #print 'city error'
                    #print tweet
                
                ### URLS
                try:
                    urls = []
                    if re.findall(web_url_regex,tweet):
                        urls.append(re.findall(WEB_URL_REGEX,tweet))
                    
                    ### IF WE DECIDE WE ONLY WANT ONE URL PER RECORD       
                    #if urls:
                        #urls = urls[0]
                except:
                    urls = []
                    #print 'url error'
                    #print tweet
                
                ### DATES
                try:
                    dates = []
                    ### SPACY NLP
                    doc = nlp(tweet)
                    ### ITERATING THROUGH ENTITIES FROM SPACY
                    for ent in doc.ents:
                        ### EXCLUDE SOME DIRTY DATES FROM TWITTER THAT SPACY MISTAKENLY INCLUDES
                        if ent.label_ == u'DATE':
                            if re.findall(date_exclude_regex,ent.text):
                                pass
                            elif re.findall(date_include_regex,ent.text) and 'weeks' not in ent.text and 'months' not in ent.text and 'old' not in ent.text:
                                dates.append(ent.text)
                                
                    ### IF WE DECIDE WE ONLY WANT ONE DATE PER RECORD       
                    #if dates:
                        #dates = dates[0]
                                    
                except:
                    dates = []
                    # print 'date error'
                    # print tweet
                
                ### LEGISLATOR NAMES
                try:
                    leg_names = []
                    if leg_name_regex.match(tweet):
                        for match in re.findall(leg_name_regex, tweet):
                            leg_names.append(match)                        
                except:
                    leg_names = []
                    # print 'legislator name error'
                    # print tweet
                    
                ### LEGISLATOR TWITTER HANDLES
                try:
                    leg_twitter_handles = []
                    if leg_twitter_regex.match(tweet):
                        for match in re.findall(leg_twitter_regex, tweet):
                            leg_twitter_handles.append(match)
                except:
                    leg_twitter_handles = []
                    # print 'legislator twitter handle error'
                    # print tweet
                
                row = {'issue': self.issue,
                       'action': self.action,
                       'id': result['_id'],
                       'es_score': result['_score'],
                       'tweet_timestamp': result['_source']['@timestamp'],
                       'query_timestamp': self.querytimestamp,
                       'tweet_user': result['_source']['user'],
                       'tweet_cities':cities,
                       'tweet_states':states,
                       'tweet_urls':urls,
                       'tweet_phone_numbers':phone_numbers,
                       'tweet_dates_ref':dates,
                       'tweet_legislator_names':leg_names,
                       'tweet_legislator_handles':leg_twitter_handles,
                       # TODO: Ross to filter 'message' section of document for address
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
        s3.upload_file(self.outfile, bucket, "/".join([upload_key
                                                       ])
                       )
        print("Removing local temp file %s" % self.outfile)
        os.remove(self.outfile)
