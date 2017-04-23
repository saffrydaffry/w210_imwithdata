#!/usr/bin/env python3
"""Grab raw data in s3 staging bucket. Process and score
 by actionability.

"""

import numpy as np
import pandas as pd
import re
import editdistance
import datetime
import boto3
import argparse
import os

from textblob import Blobber
from textblob_aptagger import PerceptronTagger
from imwithdata.es_etl.issues_actions import (
    profanity_regex
)
from io import StringIO
from datetime import datetime
from imwithdata.utils import get_ini_vals

# Configs form .ini file
# .ini location
config_file = os.path.join(os.pardir,
                           'config',
                           'config.ini'
                           )

aws_creds = get_ini_vals(config_file, 'aws.creds')
s3 = boto3.client("s3", "us-west-2",
                  aws_access_key_id=aws_creds['AWS_ACCESS_KEY_ID'],
                  aws_secret_access_key=aws_creds['AWS_SECRET_ACCESS_KEY']
                  )

# -- Constants -- #
date_format = "%y.%m.%d"
bucket = "mids-capstone-rzst"
prefix = "es_staging"
filename = "es_data.csv"

def df_from_s3(bucket, key, s3_client):
    # Download the data from s3 to pandas
    # max file size shouldn't exceed 100k rows
    buffer = StringIO()
    data = s3_client.get_object(Bucket=bucket, Key=key)
    buffer.write(data['Body'].read().decode())
    buffer.seek(0)

    return pd.read_csv(buffer)


def process_twitter(actionability_ranking: pd.DataFrame):
    """Filter actionable items.

    :param data:
    :return:
    """
    ### LOAD POS TAGGER TO HELP WITH ACTIONABILITY SCORING
    tb = Blobber(pos_tagger=PerceptronTagger())

    ### CREATE EMPTY LIST FOR SCORES FROM TEXT ANALYSIS
    language_scores = []

    ### WE DONT WANT PAST TENSE VERBS AND ADVERBS INDICATE NEWS
    bad_verbs = ['VBZ', 'VBN', 'VBD', 'RB']
    good_verbs = ['VB', 'VBG', 'VBP', 'JJ']

    # Part of speech tag each tweet
    for tweet in actionability_ranking['tweet'].tolist():
        tagged = tb(tweet.lower())
        tag_list = [x[1] for x in tagged.tags]
        score = 0

        # Penalize tweets with structures that are known to be now what we're looking for
        # POS Tags available here: https://www.ling.upenn.edu/courses/Fall_2003/ling001/penn_treebank_pos.html
        if tag_list[:2] == ['NNP', 'POS', ]:
            score -= 4
        if tag_list[:3] == ['NN', 'POS', 'NN']:
            score -= 10
        if tag_list[:3] == ['NN', 'NN', 'TO']:
            score -= 10
        if tag_list[:3] == ['NN', 'TO', 'VB']:
            score -= 10
        if tag_list[:3] == ['NN', 'NN', 'VBZ']:
            score -= 10
        if tag_list[:3] == ['NN', 'NN', 'JJ']:
            score -= 10
        if tag_list[:3] == ['NN', 'JJ', 'NN']:
            score -= 10

        if tag_list[:3] == ['JJ', 'NNS', 'VBP']:
            score -= 4
        elif tag_list[:3] == ['JJ', 'NN', 'VBG']:
            score -= 4
        elif tag_list[:3] == ['JJS', 'NN', 'JJ']:
            score -= 4
        elif tag_list[:3] == ['NN', 'NN', 'NN']:
            score -= 4
        elif tag_list[:3] == ['JJ', 'NN', 'NN']:
            score -= 4
        elif tag_list[:3] == ['JJ', 'NN', 'NNS']:
            score -= 4
        elif tag_list[:3] == ['JJ', 'NN', 'VB']:
            score -= 10
        elif tag_list[:3] == ['IN', 'JJ', 'NN']:
            score -= 10
        elif tag_list[0] == 'JJ':
            score += 3

        if tag_list[0] == 'VB':
            score += 4

        # Penalize tweets with words in them that indicate they are not useful
        if 'yesterday' in tweet.lower():
            score -= 10
        if 'last week' in tweet.lower():
            score -= 10
        if 'video' in tweet.lower():
            score -= 10
        if 'news search' in tweet.lower():
            score -= 10
        if 'town hall in facebook' in tweet.lower():
            score -= 20
        if 'townhall in facebook' in tweet.lower():
            score -= 20
        if "facebook's" in tweet.lower() and "town hall" in tweet.lower():
            score -= 20
        if 'cnn town hall' in tweet.lower():
            score -= 20
        if 'online  paper' in tweet.lower():
            score -= 20
        if 'join us' in tweet.lower():
            score -= 10
        if 'dreamhome' in tweet.lower():
            score -= 20
        if 'sales' in tweet.lower():
            score -= 20
        if 'relaxing' in tweet.lower():
            score -= 20
        if 'ice ice baby' in tweet.lower():
            score -= 20
        if 'interior design' in tweet.lower():
            score -= 20
        if 'canada' in tweet.lower():
            score -= 20
        if 'toyota' in tweet.lower():
            score -= 20
        if 'minister' in tweet.lower():
            score -= 20
        if 'uk' in tweet.lower():
            score -= 20
        if 'MP' in tweet:
            score -= 20
        if 'eu' in tweet.lower():
            score -= 20
        if 'england' in tweet.lower():
            score -= 20
        if 'furniture' in tweet.lower():
            score -= 20
        if 'kitchen' in tweet.lower():
            score -= 20
        if 'germany' in tweet.lower():
            score -= 20
        if 'south africa' in tweet.lower():
            score -= 20
        if 'News' in tweet:
            score -= 10
        if 'daily beast' in tweet.lower():
            score -= 20
        if '#design' in tweet.lower():
            score -= 20
        if '#interior' in tweet.lower():
            score -= 20
        if 'radicalisation' in tweet.lower():
            score -= 20
        if 'militancy' in tweet.lower():
            score -= 20
        if 'sharia' in tweet.lower():
            score -= 20
        if 'uncontrolled' in tweet.lower():
            score -= 20
        if 'enjoy a' in tweet.lower():
            score -= 20
        if tweet.lower().startswith('the latest'):
            score -= 20
        if 'wapo' in tweet.lower():
            score -= 20
        if 'nytimes' in tweet.lower():
            score -= 20
        if '5 things' in tweet.lower():
            score -= 20
        if 'poland' in tweet.lower():
            score -= 20
        if 'hungary' in tweet.lower():
            score -= 20
        if 'slovakia' in tweet.lower():
            score -= 20
        if 'czech' in tweet.lower():
            score -= 20
        if 'egypt' in tweet.lower():
            score -= 20
        if 'austria' in tweet.lower():
            score -= 20
        if 'germany' in tweet.lower():
            score -= 20
        if 'hiring' in tweet.lower():
            score -= 20
        if 'ice show' in tweet.lower():
            score -= 20
        if 'ice cream' in tweet.lower():
            score -= 20
        if 'secure border' in tweet.lower():
            score -= 20
        if 'hire thousands' in tweet.lower():
            score -= 20
        if 'demand congress hire' in tweet.lower():
            score -= 20
        if 'illegals' in tweet.lower():
            score -= 20
        if 'icecream' in tweet.lower():
            score -= 20
        if 'avalanche' in tweet.lower():
            score -= 20
        if 'ice cold' in tweet.lower():
            score -= 20
        if 'snow' in tweet.lower():
            score -= 20
        if 'alex jones' in tweet.lower():
            score -= 1000
        if 'viral' in tweet.lower():
            score -= 20
        if 'scotland' in tweet.lower():
            score -= 20
        if 'brexit' in tweet.lower():
            score -= 20
        if 'caretoclick' in tweet.lower():
            score -= 10
        if 'ministry' in tweet.lower():
            score -= 20
        if 'ugh' in tweet.lower():
            score -= 30
        if 'london' in tweet.lower():
            score -= 30
        if 'wales' in tweet.lower():
            score -= 30
        if '@youtube' in tweet.lower():
            score -= 20
        if 'breitbart' in tweet.lower():
            score -= 20
        if 'hypocrite' in tweet.lower():
            score -= 20
        if 'moron' in tweet.lower():
            score -= 20
        if '!!!' in tweet.lower():
            score -= 10
        if 'Take Action: Sign Petition' in tweet:
            score -= 50
        if 'petition' in tweet.lower():
            score -= 15
        if 'signandshareorg' in tweet.lower():
            score -= 10

        if re.findall(profanity_regex, tweet.lower()):
            score -= 50

        # Penalize tweets with tons of hashtags
        if tweet.count('#') > 2:
            score -= (tweet.count('#') - 2) * 5

        # Penalize tweets with tons of mentions
        if tweet.count('@') > 2:
            score -= (tweet.count('@') - 2) * 5

        # Reward tweets with good verbs and no bad verbs
        # PENALIZE TWEETS WITH BAD VERBS AND FEW GOOD VERBS
        verb_score = 0
        for tag in tag_list:
            if tag in bad_verbs:
                verb_score -= 2
            if tag in good_verbs:
                verb_score += 1
        score += int(verb_score * 1.0 / len(tag_list)) * 2

        # Reward polite tweets that encourage action
        if tweet.lower().startswith('please'):
            score += 10

        # Other score adjustments
        # Reward tweets that are longer
        score += int(len(tweet) / 60) * 4

        language_scores.append(score)

    ### ADD LANGUAGE SCORE TO PANDAS DF
    actionability_ranking['pos_score'] = np.asarray(language_scores)

    ### ADD ACTIONABILITY SCORE TO PANDAS DF BASED ON FIELDS WE EXTRACTED
    actionability_ranking['actionability_score'] = (np.where(actionability_ranking['tweet_cities'] == '', 0, 15) +
                                                    np.where(actionability_ranking['tweet_states'] == '', 0, 15) +
                                                    np.where(actionability_ranking['tweet_urls'] == '', 0, 5) +
                                                    np.where(actionability_ranking['tweet_phone_numbers'] == '', 0,
                                                             20) +
                                                    np.where(actionability_ranking['tweet_dates_ref'] == '', 0, 10) +
                                                    np.where(actionability_ranking['tweet_legislator_names'] == '', 0,
                                                             15) +
                                                    np.where(actionability_ranking['tweet_legislator_handles'] == '',
                                                             0, 15) +
                                                    np.where(actionability_ranking['tweet'].str.startswith('@'), -10,
                                                             0) +
                                                    np.where(actionability_ranking['tweet'].str.startswith('.@'), -10,
                                                             0)
                                                    )

    ### CALCULATE THE TOTAL SCORE
    actionability_ranking['total_score'] = (actionability_ranking['es_score'] +
                                            actionability_ranking['actionability_score'] +
                                            actionability_ranking['pos_score'])

    ### FILTER THE DF BY TOTAL SCORE AND ELASTIC SEARCH RELEVANCE
    filtered_data = actionability_ranking.loc[
        (actionability_ranking['total_score'] > 8.5) & (actionability_ranking['es_score'] > 7.0)]
    filtered_tweet_list = filtered_data['tweet'].tolist()
    filtered_score_list = filtered_data['total_score'].tolist()
    filtered_es_score_list = filtered_data['es_score'].tolist()

    ### DE-DUPLICATE USING EDIT-DISTANCE < 60 EDITS AS A FILTER
    ### THIS PART TAKES A WHILE: TWEETS^2 COMPARISONS. THAT'S WHY WE FILTER FIRST.
    distance_dict = {}

    for i, tweet in enumerate(filtered_tweet_list):
        for j, tweet2 in enumerate(filtered_tweet_list):
            tweet_ids = tuple(sorted([i, j]))
            if i == j:
                pass
            else:
                distance = editdistance.eval(tweet, tweet2)
                if distance <= 60:
                    distance_dict[tweet_ids] = distance

    ### FOR DUPLICATES, WE'LL TAKE THE MORE ACTIONABLE/RELEVANT OF THE TWO
    delete_indices = []

    for (i, j), v in distance_dict.items():
        if filtered_score_list[i] >= filtered_score_list[j]:
            delete_indices.append(j)
        else:
            delete_indices.append(i)

    delete_indices = list(set(delete_indices))

    ### WE DELETE ROWS WITH THE INDICES THAT WERE FOUND TO BE DUPLICATED AND LESS ACTIONABLE
    filtered_data.drop(filtered_data.index[delete_indices], inplace=True, errors='ignore')

    ### REMOVE SOME OF THE UN-NEEDED COLUMNS BEFORE PUSHING INTO DRUPAL
    final_data = filtered_data[[u'issue', u'action', u'id', u'es_score', u'total_score', u'tweet', u'tweet_timestamp',
                                u'query_timestamp', u'tweet_user', u'tweet_cities', u'tweet_states',
                                u'tweet_urls', u'tweet_phone_numbers', u'tweet_dates_ref',
                                u'tweet_legislator_names', u'tweet_legislator_handles']]

    #final_data.to_csv('/Users/brosskatz/PycharmProjects/rzst/w210_imwithdata/imwithdata/data/static_data/final_data_example.csv')
    
    return final_data


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--date', type=str,
                        default=datetime.now().date().strftime(format=date_format),
                        help='Date of queried data to pull.')
    parser.add_argument('--type', type=str,
                        default="twitter", choices=["twitter", "meetup"],
                        help="type of document to process"
                        )
    args = parser.parse_args()
    print("Processed data from %s" % args.date)
    key = "/".join([prefix, args.date, filename])

    data = df_from_s3(bucket, key, s3)

    if args.type == "twitter":
        final_data = process_twitter(data)
        print(final_data.head())
    else:
        print("Not a valid document type.")
        parser.print_help()


if __name__ == "__main__":
    main()


