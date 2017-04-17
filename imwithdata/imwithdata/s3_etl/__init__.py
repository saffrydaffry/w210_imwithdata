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
import math
import datetime
import sunlight

from tqdm import tqdm
from sunlight import congress
from sqlalchemy import create_engine
from imwithdata.es_etl.issues_actions import (
    state_regex,
    city_regex,
    web_url_regex,
    date_include_regex,
    leg_name_regex,
    leg_twitter_regex
)
from imwithdata.utils import (
    get_ini_vals,
    process_twitter
)

time_regex = re.compile(r'\d{1,2}(?:(?:am|pm)|(?::\d{1,2})(?:am|pm)?)', re.IGNORECASE)
nlp = spacy.load('en')

# filler apikey required for sunlight API
sunlight.apikey = 'thisisakey'

# --- Helpers --- #
def city_state_filter(city_state_str):
    """Process nonsense city_states

    :param city_state: 
    :return: 
    """
    if city_state_str == 'Washington, Washington':
        return 'Washington, DC'
    if city_state_str == 'Mobile':
        return ''
    else:
        return city_state_str


def city_state_process(cities, states):
    cities = cities.split("; ")
    states = states.split("; ")
    city_states_list = [", ".join([city, state]) for city in cities
                        for state in states]
    city_states = [city_state_filter(city_state_str) for city_state_str in city_states_list]

    return "; ".join(city_states)


# --- SQL Connections--- #
def conn_rzst_sql():
    """
    Function takes processed pandas dataframe and pushes to SQL. 
    config.ini must have [mysql] credentials for the Drupal database in order to work.

    df: Function takes df from twitter_batch_compare.py or similar. For legislators and townhalls, 
        it is prepared to take a .csv file from static data. 
        It tests for whether df is a dataframe before proceeding.
    data_type: Indicates how the data should be processed/structured and where it should be located in Drupal
    'append': Tells Pandas whether to 'replace', 'append',or 'fail' if the table exists. 
    We will only use 'replace' or 'append'
    """

    config_file = os.path.join(os.pardir, 'config', 'config.ini')
    print("Reading config file from %s" % config_file)
    mysql_creds = get_ini_vals(config_file, 'mysql')

    try:
        engine = create_engine(
            """mysql+pymysql://{user}:{password}@{host}:{port}/{db}""".format(user=mysql_creds['user'],
                                                                              password=mysql_creds['password'],
                                                                              host=mysql_creds['host'],
                                                                              port=mysql_creds['port'],
                                                                              db=mysql_creds['database']
                                                                              )
        )
        conn = engine.connect()
        conn.execute("select 1;")
        print("Connected to Rzst SQL!")
    except:
        print("Failed to connect!")
        raise

    return conn


def twitter(df, conn):
    """
    :param conn: sql connection
    :return: 
    """

    if isinstance(df, pd.DataFrame):
        actions = process_twitter(df)
    else:
        raise ImportError("Expected Twitter data to come in as Pandas DataFrame")

        # not sure if this is necessary

        ### Lists for extracting data and passing to final dataframe
        issue_list = actions['issue'].tolist()
        action_list = actions['action'].tolist()
        id_list = actions['id'].tolist()

        es_score_list = actions['es_score'].tolist()
        total_score_list = actions['total_score'].tolist()
        tweet_list = [tweet.capitalize() if tweet.isupper() else tweet for tweet in actions['tweet'].tolist()]
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
        all_urls = []

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

            times = re.findall(time_regex, tweet)
            times = list(set(times))
            if times:
                start_time = times[0]
            if len(times) > 1:
                end_time = times[1]
            start_times.append(start_time)
            end_times.append(end_time)

            tweet_cities = re.findall(city_regex, tweet)
            if tweet_cities:
                tweet_cities = list(set([city.title() for city in tweet_cities]))
                if len(tweet_cities) == 1:
                    city = tweet_cities[0]
                else:
                    city = '; '.join(tweet_cities)
            cities.append(city)

            tweet_states = re.findall(state_regex, tweet)
            if tweet_states:
                tweet_states = list(set(tweet_states))
                if len(tweet_states) == 1:
                    state = tweet_states[0]
                else:
                    state = '; '.join(tweet_states)
            states.append(state)

            tweet_legislators = re.findall(leg_name_regex, tweet)
            if tweet_legislators:
                if len(tweet_legislators) == 1:
                    legislator = tweet_legislators[0]
                else:
                    legislator = '; '.join(tweet_legislators)
            legislators.append(legislator)

            tweet_leg_handles = re.findall(leg_twitter_regex, tweet)
            if tweet_leg_handles:
                if len(tweet_leg_handles) == 1:
                    legislator_handle = tweet_leg_handles[0]
                else:
                    legislator_handle = '; '.join(tweet_leg_handles)
            legislator_handles.append(legislator_handle)

            phone_numbers = ''
            phone_matches = phonenumbers.PhoneNumberMatcher(tweet, "US")
            if phone_matches:
                phone_matches = list(set(phone_matches))
                if len(phone_matches) == 1:
                    phone_number = phonenumbers.format_number(match.number, phonenumbers.PhoneNumberFormat.NATIONAL)
                elif len(phone_matches) > 1:
                    phone_number = '; '.join(matches)

        urls = ''
        tweet_urls = re.findall(web_url_regex, tweet)
        if tweet_urls:
            tweet_urls = list(set(tweet_urls))
            if len(tweet_urls) == 1:
                urls = tweet_urls[0]
            else:
                urls = '; '.join(tweet_urls)
        all_urls.append(urls)

        title = tweet
        if tweet_urls:
            for urly in tweet_urls:
                title = title.replace(urly, '')
        titles.append(title)

    actions['city_state'] = actions.apply(lambda row: city_state_process(row.city, row.states),
                                          axis=1
                                          )

    ### SEND DATA TO SQL
    prepped_to_sql = pd.DataFrame(
        {'id': id_list,
         'title': [title.encode('utf-8') for title in titles],
         'description': [tweet.encode('utf-8') for tweet in tweet_list],
         'action': [action.encode('utf-8') for action in action_list],
         'issue': [issue.encode('utf-8') for issue in issue_list],
         'total_score': total_score_list,
         'relevance_score': es_score_list,
         'legislators': legislators,
         'legislator_twitter': legislator_handles,
         'city': cities,
         'state': states,
         'city_state': city_states,
         'phone_number': phone_numbers,
         'urls': [url.encode('utf-8') for url in all_urls],
         'date_of_action': dates,
         'announced_date': tweet_timestamp_list,
         'query_date': query_timestamp_list
         })

    prepped_to_sql.to_sql('rzst_action',
                          conn,
                          if_exists='append',
                          index=False)


def legislators(df, conn):

    if isinstance(df, pd.DataFrame):
        legislator_df = df
    else:
        legislator_df = pd.read_csv(df, encoding='utf-8')

    final_legislator_df = legislator_df[['title', 'first_name', 'last_name', 'state', 'state_name', 'party', 'website',
                                         'phone', 'oc_email', 'contact_form']]

    final_legislator_df.sort_values(['state_name'], ascending=[True], inplace=True)

    final_legislator_df.to_sql('rzst_legislators',
                               conn,
                               if_exists='replace',
                               index=False
                               )


def townhalls(df, conn):
    if isinstance(df, pd.DataFrame):
        townhalls = df
    else:
        townhalls = pd.read_csv(df,
                                   encoding='utf-8'
                                   )

    townhalls['event_id'] = townhalls['|']
    townhalls['event_source'] = 'Townhall Project'
    townhalls['event_score'] = 65
    townhalls['event_issues'] = 'All Issues'
    townhalls['event_title'] = townhalls['|__Member'] + ' ' + townhalls['|__meetingType']
    townhalls['event_description'] = townhalls['|__Notes'].str.encode('utf-8')
    townhalls['event_location_name'] = townhalls['|__Location']
    townhalls['event_address'] = townhalls['|__address']
    townhalls['event_city'] = townhalls['|__City']
    townhalls['event_state'] = townhalls['|__State']
    townhalls['event_zip'] = townhalls['|__Zip']
    townhalls['event_district'] = townhalls['|__District']
    townhalls['event_full_address'] = (townhalls['|__Location'].map(str) + ', ' + townhalls['|__address'].map(str) + ', '
                                       + townhalls['|__City'].map(str) + ', ' + townhalls['|__State'].map(str) + ' '
                                       + townhalls['|__Zip'].map(str))
    townhalls['event_location_phone'] = ''
    townhalls['event_rsvp_to'] = townhalls['|__RSVP']
    townhalls['event_lat'] = townhalls['|__lat']
    townhalls['event_lng'] = townhalls['|__lng']
    townhalls['event_date'] = pd.to_datetime(townhalls['|__yearMonthDay']).dt.strftime('%Y-%m-%d')
    townhalls['event_start_time'] = townhalls['|__timeStart24']
    townhalls['event_end_time'] = townhalls['|__timeEnd24']
    townhalls['event_time_zone'] = townhalls['|__timeZone']
    townhalls['event_url'] = townhalls['|__link']
    townhalls['event_group_associated'] = 'Townhall Project'
    townhalls['event_group_url'] = 'https://townhallproject.com'
    townhalls['event_legislator'] = townhalls['|__Member']
    townhalls['event_meeting_type'] = townhalls['|__meetingType']

    townhalls_final = townhalls[['event_id',
                                 'event_score',
                                 'event_issues',
                                 'event_title',
                                 'event_description',
                                 'event_location_name',
                                 'event_address',
                                 'event_city',
                                 'event_state',
                                 'event_zip',
                                 'event_district',
                                 'event_full_address',
                                 'event_location_phone',
                                 'event_rsvp_to',
                                 'event_lat',
                                 'event_lng',
                                 'event_date',
                                 'event_start_time',
                                 'event_end_time',
                                 'event_time_zone',
                                 'event_url',
                                 'event_group_associated',
                                 'event_group_url',
                                 'event_legislator',
                                 'event_meeting_type']]

    townhalls = townhalls_final[['event_title',
                                 'event_description',
                                 'event_location',
                                 'event_date',
                                 'event_time',
                                 'event_url',
                                 'event_related_state',
                                 'event_legislator',
                                 'event_meeting_type'
                                 ]]
    # if event_url blank, fill with townhall.com
    townhalls['event_url'] = townhalls['event_url'].fillna(value="https://townhallproject.com")

    townhalls_final.drop_duplicates(inplace=True)

    mask = (pd.to_datetime(townhalls_final['event_date']) > datetime.datetime.today())

    townhalls_final = townhalls_final[mask]

    townhalls_final.to_sql('rzst_events',
                           conn,
                           if_exists='append',
                           index=False)


def meetup(meetup_df, conn):
    temp_row = dict.fromkeys([
        'event_id',
        'event_source',
        'event_score',
        'event_issues',
        'event_title',
        'event_description',
        'event_location_name',
        'event_address',
        'event_city',
        'event_state',
        'event_zip',
        'event_district',
        'event_full_address',
        'event_location_phone',
        'event_rsvp_to',
        'event_lat',
        'event_lng',
        'event_date',
        'event_start_time',
        'event_end_time',
        'event_time_zone',
        'event_url',
        'event_group_associated',
        'event_group_url',
        'event_legislators',
        'event_districts',
        'event_meeting_type'
    ])
    new_df = []
    count = 0
    badrows = 0
    for index, row in tqdm(meetup_df.iterrows()):
        try:
            lat = row['_source.group.lat']
            if lat:
                associated_legislators = '; '.join([leg['title'] + '. ' + leg['first_name'] + ' ' + leg['last_name']
                                                    for leg in congress.locate_legislators_by_lat_lon(lat,row['_source.group.lon'])])
                associated_districts = '; '.join([dist['state'] + '-' + str(dist['district']).zfill(2)
                                                    for dist in congress.locate_districts_by_lat_lon(lat,row['_source.group.lon'])])
            else:
                associated_legislators = ''
                associated_districts = ''
                
            temp_row['event_legislators'] = associated_legislators
            temp_row['event_districts'] = associated_districts

            timedelt = pd.Timedelta(milliseconds=row['_source.utc_offset'])

            duration = row['_source.duration']
            eventdelt = (pd.Timedelta(milliseconds=duration) if math.isnan(duration) == False else 0.0)

            temp_row['event_id'] = row['_id']
            temp_row['event_source'] = 'Meetup.com'
            temp_row['event_score'] = row['_score'] * 100
            temp_row['event_issues'] = row['_index']
            temp_row['event_title'] = row['_source.name']
            temp_row['event_description'] = row['_source.description'].str.encode('utf-8')
            temp_row['event_location_name'] = row['_source.venue.name']
            temp_row['event_address'] = row['_source.venue.address_1']
            temp_row['event_city'] = row['_source.venue.city']
            temp_row['event_state'] = row['_source.venue.state']
            temp_row['event_zip'] = row['_source.venue.zip']
            temp_row['event_district'] = row['districts']
            temp_row['event_full_address'] = (row['event_location_name'].map(str) + ', ' +
                                                 row['event_address'].map(str) + ', ' +
                                                 row['event_city'].map(str) + ', ' +
                                                 row['event_state'].map(str) + ' ' +
                                                 row['event_zip'].map(str))
            temp_row['event_location_phone'] = row['_source.venue.phone']
            temp_row['event_rsvp_to'] = row['_source.link']
            temp_row['event_lat'] = row['_source.venue.lat']
            temp_row['event_lng'] = row['_source.venue.lon']
            temp_row['event_date'] = ((pd.to_datetime(row['_source.time']) -
                                         timedelt).dt.strftime('%Y-%m-%d'))
            temp_row['event_start_time'] = ((pd.to_datetime(row['_source.time']) -
                                                timedelt).dt.strftime('%H:%M'))
            temp_row['event_end_time'] = ((pd.to_datetime(row['_source.time']) +
                                              eventdelt).dt.strftime('%H:%M'))
            temp_row['event_time_zone'] = ''
            temp_row['event_url'] = row['_source.link']
            temp_row['event_group_associated'] = row['_source.group.name']
            temp_row['event_group_url'] = "https://www.meetup.com/"
            temp_row['event_meeting_type'] = 'Meetup'

            new_df.append(temp_row)
        except Exception as e:
            print("Error with row %s" % count)
            print(row)
            print(e)
            badrows += 1
        count += 1
        print("Number of errors %s" % badrows)

    return pd.DataFrame(new_df)


# def meetup(df, conn):
#     if isinstance(df, pd.DataFrame):
#         meetup_data = df
#     else:
#         meetup_data = pd.DataFrame(df)
#
#     associated_legislators = []
#     associated_districts = []
#
#     for i, lat in enumerate(meetup_data['_source.group.lat'].tolist()):
#         if lat:
#             legs = '; '.join([leg['title'] + '. ' + leg['first_name'] + ' ' + leg['last_name']
#                               for leg in
#                               congress.locate_legislators_by_lat_lon(lat, meetup_data['_source.group.lon'].tolist()[i])])
#             dists = '; '.join([dist['state'] + '-' + str(dist['district']).zfill(2)
#                                for dist in
#                                congress.locate_districts_by_lat_lon(lat, meetup_data['_source.group.lon'].tolist()[i])])
#         else:
#             legs = ''
#             dists = ''
#         associated_legislators.append(legs)
#         associated_districts.append(dists)
#
#     meetup_data['legislators'] = associated_legislators
#     meetup_data['districts'] = associated_districts
#
#     meetup_data = meetup_rows(meetup_data)
#     meetup_data['timedelt'] = pd.Series([pd.Timedelta(milliseconds=i) for i in
#                                          meetup_data['_source.utc_offset'].tolist()])
#     meetup_data['event_delt'] = pd.Series([pd.Timedelta(milliseconds=i)
#                                            if math.isnan(i) == False else 0.0
#                                            for i in meetup_data['_source.duration'].tolist()])
#
#     meetup_data['event_id'] = meetup_data['_id']
#     meetup_data['event_source'] = 'Meetup.com'
#     meetup_data['event_score'] = meetup_data['_score'] * 100
#     meetup_data['event_issues'] = meetup_data['_index']
#     meetup_data['event_title'] = meetup_data['_source.name']
#     meetup_data['event_description'] = meetup_data['_source.description'].str.encode('utf-8')
#     meetup_data['event_location_name'] = meetup_data['_source.venue.name']
#     meetup_data['event_address'] = meetup_data['_source.venue.address_1']
#     meetup_data['event_city'] = meetup_data['_source.venue.city']
#     meetup_data['event_state'] = meetup_data['_source.venue.state']
#     meetup_data['event_zip'] = meetup_data['_source.venue.zip']
#     meetup_data['event_district'] = meetup_data['districts']
#     meetup_data['event_full_address'] = (meetup_data['event_location_name'].map(str) + ', ' +
#                                          meetup_data['event_address'].map(str) + ', ' +
#                                          meetup_data['event_city'].map(str) + ', ' +
#                                          meetup_data['event_state'].map(str) + ' ' +
#                                          meetup_data['event_zip'].map(str))
#     meetup_data['event_location_phone'] = meetup_data['_source.venue.phone']
#     meetup_data['event_rsvp_to'] = meetup_data['_source.link']
#     meetup_data['event_lat'] = meetup_data['_source.venue.lat']
#     meetup_data['event_lng'] = meetup_data['_source.venue.lon']
#     meetup_data['event_date'] = ((pd.to_datetime(meetup_data['_source.time']) -
#                                   meetup_data['timedelt']).dt.strftime('%Y-%m-%d'))
#     meetup_data['event_start_time'] = ((pd.to_datetime(meetup_data['_source.time']) -
#                                         meetup_data['timedelt']).dt.strftime('%H:%M'))
#     meetup_data['event_end_time'] = ((pd.to_datetime(meetup_data['_source.time']) +
#                                       meetup_data['event_delt']).dt.strftime('%H:%M'))
#     meetup_data['event_time_zone'] = ''
#     meetup_data['event_url'] = meetup_data['_source.link']
#     meetup_data['event_group_associated'] = meetup_data['_source.group.name']
#     meetup_data['event_group_url'] = "https://www.meetup.com/"
#     meetup_data['event_legislator'] = meetup_data['legislators']
#     meetup_data['event_meeting_type'] = 'Meetup'
#
#     meetup_final = meetup_data[[
#         'event_id',
#         'event_source',
#         'event_score',
#         'event_issues',
#         'event_title',
#         'event_description',
#         'event_location_name',
#         'event_address',
#         'event_city',
#         'event_state',
#         'event_zip',
#         'event_district',
#         'event_full_address',
#         'event_location_phone',
#         'event_rsvp_to',
#         'event_lat',
#         'event_lng',
#         'event_date',
#         'event_start_time',
#         'event_end_time',
#         'event_time_zone',
#         'event_url',
#         'event_group_associated',
#         'event_group_url',
#         'event_legislator',
#         'event_meeting_type'
#     ]]
#
#     meetup_final.drop_duplicates(inplace=True)
#
#     mask = (pd.to_datetime(meetup_final['event_date']) > datetime.datetime.today())
#
#     meetup_final = meetup_final[mask]
#
#     meetup_final.to_sql('rzst_events', conn, if_exists='append', index=False)
