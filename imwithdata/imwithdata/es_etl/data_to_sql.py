#!/usr/bin/env python3
"""Take output of actionability scoring. 
Clean data for input into Drupal Table.


"""

import pandas as pd
import sqlalchemy
import pandas as pd
import os
import spacy
import re
import phonenumbers

from sqlalchemy import create_engine
from imwithdata.es_etl.issues_actions import (
    state_regex,
    city_regex,
    web_url_regex,
    date_include_regex,
    leg_name_regex,
    leg_twitter_regex
)
from imwithdata.utils import get_ini_vals

time_regex = re.compile(r'\d{1,2}(?:(?:am|pm)|(?::\d{1,2})(?:am|pm)?)', re.IGNORECASE)
nlp = spacy.load('en')


#### THIS IS THE FUNCTION TO IMPORT
def data_to_sql(output_data_frame, data_type = 'twitter', to_existing_data = 'append'):
    """
    Function takes processed pandas dataframe and pushes to SQL. config.ini must have [mysql] credentials for the Drupal database in order to work.
    
    output_data_frame: Function takes output_data_frame from twitter_batch_compare.py or similar 
    data_type: Indicates how the data should be processed/structured and where it should be located in Drupal
    to_existing_data: Tells Pandas whether to 'replace', 'append',or 'fail' if the table exists. We will only use 'replace' or 'append'
    """
    
    config_file = os.path.join(os.pardir, 'config', 'config.ini')

    mysql_creds = get_ini_vals(config_file, 'mysql')
    
    engine = create_engine(
        """mysql+pymysql://{user}:{password}@{host}:{port}/{db}""".format(user=mysql_creds['user'],
                                                                          password=mysql_creds['password'],
                                                                          host=mysql_creds['host'],
                                                                          port=mysql_creds['port'],
                                                                          db=mysql_creds['database']
                                                                          )
                    )
    
    conn = engine.connect()
    
    actions = output_data_frame.sort('total_score', ascending=[0])
    
    if data_type == 'twitter':
        
        ### Lists for extracting data and passing to final dataframe
        issue_list = actions['issue'].tolist()
        action_list = actions['action'].tolist()
        id_list = actions['id'].tolist()

        es_score_list = actions['es_score'].tolist()
        total_score_list = actions['total_score'].tolist()
        tweet_list = actions['tweet'].tolist()
        tweet_timestamp_list = actions['tweet_timestamp'].tolist()
        query_timestamp_list = actions['query_timestamp'].tolist()
        user_list = actions['tweet_user'].tolist()
        
        ### Empty buckets for final data extraction
        dates = []
        start_times = []
        end_times = []
        cities = []
        states = []
        legislators = []
        legislator_handles = []
        phone_numbers = []
        titles = []

        for i, tweet in enumerate(tweet_list):
            date = ''
            start_time = ''
            end_time = ''
            city = ''
            state = ''
            legislator = ''
            legislator_handle = ''
            phone_number = ''
            url = ''
            title = ''

            doc = nlp(tweet)
            all_dates = [doc.text for doc in doc.ents if doc.label_ == 'DATE']
            date_matches = re.findall(date_include_regex, ' '.join(all_dates))

            ### EXCLUDE SOME DIRTY DATES FROM TWITTER THAT SPACY MISTAKENLY INCLUDES
            if date_matches:
                date = all_dates[0]
            dates.append(date)

            times = re.findall(time_regex,tweet)
            if times:
                start_time = times[0]
            if len(times) > 1:
                end_time = times[1]
            start_times.append(start_time)
            end_times.append(end_time)

            tweet_cities = re.findall(city_regex,tweet)
            if tweet_cities:
                tweet_cities = list(set([city.title() for city in tweet_cities]))
                if len(tweet_cities) == 1:
                    city = tweet_cities[0]
                else:
                    city = '; '.join(tweet_cities)
            cities.append(city)

            tweet_states = re.findall(state_regex,tweet)
            if tweet_states:
                tweet_states = list(set(tweet_states))
                if len(tweet_states) == 1:
                    state = tweet_states[0]
                else:
                    state = '; '.join(tweet_states)
            states.append(state)

            tweet_legislators = re.findall(leg_name_regex,tweet)
            if tweet_legislators:
                if len(tweet_legislators) == 1:
                    legislator = tweet_legislators[0]
                else:
                    legislator = '; '.join(tweet_legislators)
            legislators.append(legislator)

            tweet_leg_handles = re.findall(leg_twitter_regex,tweet)
            if tweet_leg_handles:
                if len(tweet_leg_handles) == 1:
                    legislator_handle = tweet_leg_handles[0]
                else:
                    legislator_handle = '; '.join(tweet_leg_handles)
            legislator_handles.append(legislator_handle)

            if phonenumbers.PhoneNumberMatcher(tweet, "US"):
                for i,match in enumerate(phonenumbers.PhoneNumberMatcher(tweet, "US")):
                    if i == 0:  
                        phone_number = phonenumbers.format_number(match.number,
                                                                    phonenumbers.PhoneNumberFormat.NATIONAL)
            phone_numbers.append(phone_number)

            tweet_urls = re.findall(web_url_regex,tweet)
            title = tweet
            if tweet_urls:
                for urly in tweet_urls:
                    title = title.replace(urly,'')
            titles.append(title)
        
        
            prepped_to_sql = pd.DataFrame(
                        {'id': id_list,
                         'title': [title.encode('utf-8') for title in titles],
                         'description': [tweet.encode('utf-8') for tweet in tweet_list],
                         'action': [action.encode('utf-8') for action in action_list],
                         'issue': [issue.encode('utf-8') for issue in issue_list],
                         'total_score':total_score_list,
                         'relevance_score':es_score_list,
                         'legislators': legislators,
                         'legislator_twitter': legislator_handles,
                         'city':cities,
                         'state':states,
                         'phone_number': phone_numbers,
                         'date_of_action': dates,
                         'announced_date': tweet_timestamp_list,
                         'query_date':query_timestamp_list
                        })
            
            prepped_to_sql.to_sql('rzst_action',
                                  conn,
                                  if_exists=to_existing_data,
                                  index=False)

    
    