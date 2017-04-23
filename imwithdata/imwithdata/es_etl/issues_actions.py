#!/usr/bin/env python3
"""Lists that keep track of issues, actions, keywords

"""
import pandas as pd
import sunlight
import os
import re

from sunlight import congress
from imwithdata import PROJECT_ROOT

issues = ['civil_right',
          'healthcare',
          'voting',
          'speech',
          'immigrants',
          'lgbt',
          'worker',
          'womens_right',
          'climate',
          'rzst',
          ''
          ]

actions = {'charity': ["donat*",
                       "donate",
                       "give support",
                       "financial support"
                       ],
           'protest': ['protest',
                       'march'
                       ],
           'petition': ['petition',
                        'sign',
                        'call'
                        ],
           'gathering': ["meetup",
                         "huddle",
                         "congregate",
                         "join us"
                         ],
            'write': ["write postcard",
                         "write letter",
                         "make signs",
                        "make a sign"
                         ],
           'boycott': ["boycott"],
           'advocate': ["call",
                        "email",
                        "reach out",
                        "senator",
                        "representative",
                        "sign petition",
                        "petition"
                        ],
           'vote': ["vote",
                    "cast your ballot"],
           'townhall': ["town hall",
                        "open office",
                        "town meeting",
                        "townhall",
                        'virtual townhall']
           }

# Original list of tags, used in ES pull
issue_tags = {'Healthcare': ['healthcare.gov',
                             'aca',
                             'obamacare',
                             'affordable+care+act',
                             'medicare',
                             'medicaid',
                             'health+care',
                             'veterans+care',
                             'vca',
                             'health+insurance',
                             '#ACA',
                             '@HealthCareGov',  # Official ACA Handle
                             'single+payer',
                             '#SinglePayerNow',
                             '#CareNotChaos'
                             ],
              'Women': ['@womensmarch',
                        '@WomensVoicesNow',
                        '#PPAct',
                        '#PPActionCA',  # PP Act for Cali
                        'birth+control',
                        '#StandWithPP',
                        '#trustwomen',
                        '#neverthelessshepersisted',
                        '#PussyhatProject',
                        '#adaywithoutwomen',
                        '#adaywithoutawoman',
                        '@WhyIMarch',
                        '#whyimarch',
                        "womens+rights",
                        '@LWV',  # league of women voters
                        '#genderequality',
                        'gender+equality',
                        "planned+parenthood",
                        'equal+pay',
                        '@WomensVoicesNow'

                        ],
              'Climate': ['climate+change',
                          '#climatechange'
                          'epa',
                          '@EPA',
                          'global+warming',
                          '@Interior',  # US Dept of Interior
                          '@algore',  # Al Gore
                          '@UNFCCC',  # UN Climate Secretariat
                          '#GlobalWarming',
                          'sustainability',
                          '@SierraClub',
                          '#environment',
                          '#cleanwater',
                          '#climatemarch',
                          '#GlobalWarming',
                          ],
              'immigrants': ['immigrants',
                             "refugees",
                             'refugee+rights',
                             'travel+ban',
                             'border+wall',
                             'refugees',
                             'muslim+ban',
                             'ICE',
                             'border+patrol',
                             'customs+and+border'
                             'asylum',
                             'immigration+reform',
                             'immigrant+advocacy',
                             'migrant+rights',
                             'undocumented',
                             '@MuslimAdvocates'
                             '#immigrantrights',
                             '#immigrant',
                             '#muslimban',
                             '#nobannowall',
                             'citizenship+test',
                             'religious+test'

                             ],
              "civil": ["racial+equality",
                        "black+lives+matter",
                        "african+american+rights",
                        "black+rights"
                        "civil+rights",
                        '#civilrights',
                        '@ADL_National',
                        '@splcenter',
                        '@civilrightsorg'
                        '@NAACP',
                        '@ACLU',
                        "black+power",
                        "jim+crow",
                        '#aclu',
                        '#civilrights',
                        '@peoplepower',
                        '#peoplepower',
                        '@CCCAction'

                        ],
              "LGBT": ["marriage+equality",
                       "transgender+rights",
                       "equality+act",
                       "lesbian+rights",
                       'gay+rights',
                       'gay+marriage',
                       '#LGBTQ',
                       '#GLBT',
                       '#LGBT',
                       '#LGBTI',
                       '@lsarsour',
                       '#EqualityAct'
                       '@Dyke67ny',  ## LGBT Equality handle
                       '#Pride',
                       '#PrideFlag',
                       '@gaycivilrights',
                       '@HappyRights',
                       '#gayrights',
                       '@GayRightsMedia',
                       '@gay_rights',
                       'LGBT+adoption'

                       ],
              "voter": ["redistricting",
                        "gerrymandering",
                        "redistrict",
                        "gerrymander",
                        "voter+id",
                        "voting+access",
                        "voter+access",
                        "voter+suppression",
                        'voting+rights'
                        '#votingrights',
                        '@VotingMatters',
                        '@LWV',
                        '#votersuppression',
                        '#voting',
                        '@Let_AmericaVote',
                        '#VoterSuppression',
                        'popular+vote',
                        'electoral+college'

                        ],
              "worker": ['worker+rights',
                         'minimum+wage',
                         '@4WorkerRights',
                         '#worker',
                         '#Workerrights',
                         'labor_rights',
                         '@4US_Workers',
                         '@AFLCIO',
                         '#SaveQualityJobs',
                         'US+workers',
                         '@steelworkers',
                         '@unitehere',
                         '@MinimumWageBiz',
                         '@SEIU'

                         ],
              'speech': ['@PressFreedom',
                         'freedom+of+speech',
                         'freedom+of+the press',
                         '#ProtectPressFreedom',
                         '#SavePBS',
                         '#FreePress',
                         '@FreeSpeechDaily',
                         '@FreeThePressNow',
                         '@FreedomofPress',
                         '#1stAmendment',
                         '#thisisdemocracy',
                         '#resist',
                         '#theresistance',
                         'first+amendment',
                         '1st+amendment'
                         ]
              }

states = ['Alabama', 'Alaska', 'Arizona', 'Arkansas', 'District of Columbia', 'California', 'Colorado',
          'Connecticut', 'Delaware', 'Florida', 'Georgia',
          'Hawaii', 'Idaho', 'Illinois', 'Indiana', 'Iowa', 'Kansas', 'Kentucky', 'Louisiana', 'Maine', 'Maryland',
          'Massachusetts', 'Michigan', 'Minnesota', 'Mississippi', 'Missouri', 'Montana', 'Nebraska', 'Nevada',
          'New Hampshire', 'New Jersey', 'New Mexico', 'New York', 'North Carolina', 'North Dakota', 'Ohio', 'Oklahoma',
          'Oregon', 'Pennsylvania', 'Rhode Island', 'South Carolina', 'South Dakota', 'Tennessee', 'Texas', 'Utah',
          'Vermont', 'Virginia', 'Washington', 'West Virginia', 'Wisconsin', 'Wyoming', 'ALABAMA', 'ALASKA', 'ARIZONA',
          'ARKANSAS', 'DISTRICT OF COLUMBIA', 'CALIFORNIA', 'COLORADO', 'CONNECTICUT', 'DELAWARE', 'FLORIDA', 'GEORGIA',
          'HAWAII', 'IDAHO', 'ILLINOIS', 'INDIANA', 'IOWA', 'KANSAS', 'KENTUCKY', 'LOUISIANA', 'MAINE', 'MARYLAND',
          'MASSACHUSETTS', 'MICHIGAN', 'MINNESOTA', 'MISSISSIPPI', 'MISSOURI', 'MONTANA', 'NEBRASKA', 'NEVADA',
          'NEW HAMPSHIRE', 'NEW JERSEY', 'NEW MEXICO', 'NEW YORK', 'NORTH CAROLINA', 'NORTH DAKOTA', 'OHIO', 'OKLAHOMA',
          'OREGON', 'PENNSYLVANIA', 'RHODE ISLAND', 'SOUTH CAROLINA', 'SOUTH DAKOTA', 'TENNESSEE', 'TEXAS', 'UTAH',
          'VERMONT', 'VIRGINIA', 'WASHINGTON', 'WEST VIRGINIA', 'WISCONSIN', 'WYOMING', 'NY', 'NYC']

state_abbrevs = ['IA', 'KS', 'UT', 'MA', 'MI', 'MO',
                 'VA', 'NC', 'NE', 'SD', 'AL', 'ID', 'FM', 'DE', 'AK', 'Conn', 'NM', 'MS', 'GA',
                 'CO', 'NJ', 'FL', 'MN', 'NV', 'AZ', 'WI', 'ND', 'OK', 'KY', 'RI', 'NH', 'MO', 'ME', 'VT',
                 'NY', 'CA', 'HI', 'IL', 'TN', 'Mass', 'OH', 'MD', 'MI', 'WY', 'WA', 'SC', 'PA',
                 'IN', 'LA', 'DC', 'AR', 'WV', 'TX', 'Minn', 'Ark', 'Ind', 'D\.C\.',
                 'Mizz', 'Nev', 'Okl', 'Penn', 'S\. Carolina', 'N\. Carolina', 'S Carolina', 'N Carolina', 'Tenn',
                 'Tex']

state_regex = re.compile(r'(\\b' + '|\\b'.join(states) + '|' + '|'.join([state + '\\b' for state in states])
                         + '|' + '|'.join(['\\b' + state + '\\b' for state in state_abbrevs]) + r')')
cities = pd.read_csv(os.path.join(PROJECT_ROOT,
                                  'data',
                                  'Top5000Population.csv')
                     )
#city_list = list(set(list(cities['city'].str.rstrip())))
#state_list = list(cities['state'].str.rstrip())
#city_state_list = [city + '+, ' + states[i] for i, city in enumerate(city_list)]

city_list = cities.city.tolist()
state_list = cities.state.tolist()
city_state_list = [city + ", " + state for city, state in list(zip(city_list, state_list))]

city_regex = re.compile(r'\b(' + '|'.join(city_state_list + city_list
                                          + ['LA', 'NYC', 'DC', "L\.A\.", 'N\.Y\.C.', "D\.C\.", "Philly", "PHL", "SF",
                                             "S\.F\.",
                                             "DFW", "KC", "OC"]) +
                        r')\b', re.IGNORECASE)

web_url_regex = r"""(?i)\b((?:https?:(?:/{1,3}|[a-z0-9%])|[a-z0-9.\-]+[.](?:com|net|org|edu|gov|mil|aero|asia|biz|cat|coop|info|int|jobs|mobi|museum|name|post|pro|tel|travel|xxx|ac|ad|ae|af|ag|ai|al|am|an|ao|aq|ar|as|at|au|aw|ax|az|ba|bb|bd|be|bf|bg|bh|bi|bj|bm|bn|bo|br|bs|bt|bv|bw|by|bz|ca|cc|cd|cf|cg|ch|ci|ck|cl|cm|cn|co|cr|cs|cu|cv|cx|cy|cz|dd|de|dj|dk|dm|do|dz|ec|ee|eg|eh|er|es|et|eu|fi|fj|fk|fm|fo|fr|ga|gb|gd|ge|gf|gg|gh|gi|gl|gm|gn|gp|gq|gr|gs|gt|gu|gw|gy|hk|hm|hn|hr|ht|hu|id|ie|il|im|in|io|iq|ir|is|it|je|jm|jo|jp|ke|kg|kh|ki|km|kn|kp|kr|kw|ky|kz|la|lb|lc|li|lk|lr|ls|lt|lu|lv|ly|ma|mc|md|me|mg|mh|mk|ml|mm|mn|mo|mp|mq|mr|ms|mt|mu|mv|mw|mx|my|mz|na|nc|ne|nf|ng|ni|nl|no|np|nr|nu|nz|om|pa|pe|pf|pg|ph|pk|pl|pm|pn|pr|ps|pt|pw|py|qa|re|ro|rs|ru|rw|sa|sb|sc|sd|se|sg|sh|si|sj|Ja|sk|sl|sm|sn|so|sr|ss|st|su|sv|sx|sy|sz|tc|td|tf|tg|th|tj|tk|tl|tm|tn|to|tp|tr|tt|tv|tw|tz|ua|ug|uk|us|uy|uz|va|vc|ve|vg|vi|vn|vu|wf|ws|ye|yt|yu|za|zm|zw)/)(?:[^\s()<>{}\[\]]+|\([^\s()]*?\([^\s()]+\)[^\s()]*?\)|\([^\s]+?\))+(?:\([^\s()]*?\([^\s()]+\)[^\s()]*?\)|\([^\s]+?\)|[^\s`!()\[\]{};:'".,<>?«»“”‘’])|(?:(?<!@)[a-z0-9]+(?:[.\-][a-z0-9]+)*[.](?:com|net|org|edu|gov|mil|aero|asia|biz|cat|coop|info|int|jobs|mobi|museum|name|post|pro|tel|travel|xxx|ac|ad|ae|af|ag|ai|al|am|an|ao|aq|ar|as|at|au|aw|ax|az|ba|bb|bd|be|bf|bg|bh|bi|bj|bm|bn|bo|br|bs|bt|bv|bw|by|bz|ca|cc|cd|cf|cg|ch|ci|ck|cl|cm|cn|co|cr|cs|cu|cv|cx|cy|cz|dd|de|dj|dk|dm|do|dz|ec|ee|eg|eh|er|es|et|eu|fi|fj|fk|fm|fo|fr|ga|gb|gd|ge|gf|gg|gh|gi|gl|gm|gn|gp|gq|gr|gs|gt|gu|gw|gy|hk|hm|hn|hr|ht|hu|id|ie|il|im|in|io|iq|ir|is|it|je|jm|jo|jp|ke|kg|kh|ki|km|kn|kp|kr|kw|ky|kz|la|lb|lc|li|lk|lr|ls|lt|lu|lv|ly|ma|mc|md|me|mg|mh|mk|ml|mm|mn|mo|mp|mq|mr|ms|mt|mu|mv|mw|mx|my|mz|na|nc|ne|nf|ng|ni|nl|no|np|nr|nu|nz|om|pa|pe|pf|pg|ph|pk|pl|pm|pn|pr|ps|pt|pw|py|qa|re|ro|rs|ru|rw|sa|sb|sc|sd|se|sg|sh|si|sj|Ja|sk|sl|sm|sn|so|sr|ss|st|su|sv|sx|sy|sz|tc|td|tf|tg|th|tj|tk|tl|tm|tn|to|tp|tr|tt|tv|tw|tz|ua|ug|uk|us|uy|uz|va|vc|ve|vg|vi|vn|vu|wf|ws|ye|yt|yu|za|zm|zw)\b/?(?!@)))"""

dates_dont_include = ['year old', 'old', 'decades', 'year olds', 'ago', 'ryear', 'calendar', '1 or 2', 'weeks', 'year',
                      'years', 'days', 'old', 'olds', '80s', '90s', '%', '1k', '2k', '3k', '4k', '5k', '6k', '7k', '8k',
                      '9k', '10k', '0k', 'weeks', 'months', 'more', 'anniversary', 'yr', '@', 'past', 'circa', 'last',
                      'later', 'yesterday', 'yall', 'you', 'up to', 'illegal', '50/50', 'Free', '100 Days', 'many', '#',
                      'ly', 'Rs', 'up to']

dates_include = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October',
                 'November', 'December', '1/', '2/', '3/', '4/', '5/', '6/', '7/', '8/', '9/', '10/', '11/', '12/',
                 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec', '2017/', '2018/',
                 '2019/', '01/', '02/', '03/', '04/', '05/', '06/', '07/', '08/', '09/', '10/', '11/', '12/', '7am',
                 '8am', '9am', '10am', '11am', '12am', '1pm', '2pm', '3pm', '4pm', '5pm', '6pm', '7pm', '8pm', '9pm',
                 '10pm', '11pm', '12am', '7:00 AM', '8:00 AM', '9:00 AM', '10:00 AM', '11:00 AM', '12:00 PM', '1:00 PM',
                 '2:00 PM', '3:00 PM', '4:00 PM', '5:00 PM', '6:00 PM', '7:00 PM', '8:00 PM', '9:00 PM', '10:00 PM',
                 '11:00 PM', '12:00 AM', '7:00AM', '8:00AM', '9:00AM', '10:00AM', '11:00AM', '12:00PM', '1:00PM',
                 '2:00PM', '3:00PM', '4:00PM', '5:00PM', '6:00PM', '7:00PM', '8:00PM', '9:00PM', '10:00PM', '11:00PM',
                 '12:00AM', '7 AM', '8 AM', '9 AM', '10 AM', '11 AM', '12 PM', '1 PM', '2 PM', '3 PM', '4 PM', '5 PM',
                 '6 PM', '7 PM', '8 PM', '9 PM', '10 PM', '11 PM', '12 AM', 'Monday', 'Tuesday', 'Wednesday',
                 'Thursday', 'Friday', 'Saturday', 'Sunday', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun', 'Today',
                 'Tomorrow', 'Day after Tomorrow', 'Day after ', 'Everyday this week', 'Every day this week',
                 'Everyday this month', 'every day this month', 'next 2', 'next 3', 'next 4', 'next 5', 'next 6',
                 'next 7', 'next 8', 'next 9', 'next 10', 'this week', 'next week', 'two weeks', 'three weeks',
                 'four weeks', '2 weeks', '3 weeks', '4 weeks', 'this weekend', 'next Monday', 'next Tuesday',
                 'next Wednesday', 'next Thursday', 'next Friday', 'next Saturday', 'next Sunday', 'this Mon',
                 'this Tue', 'this Wed', 'this Thur', 'this Fri', 'This Sat', 'This Sun', 'ThisWeek',
                 '1st', '2nd', '3rd', '4th', '5th', '6th', '7th', '8th', '9th']

profanity = ['anal', 'anus', 'ass', 'asshole', 'asshole.', 'ballsack', 'blowjob', 'blow job', 'boner', 'clitoris',
             'cock', 'cunt', 'dick', 'dildo', 'dyke', 'fag', 'fuck', 'jizz', 'labia', 'muff', 'nigger', 'nigga', 'nigg',
             'penis', 'piss', 'pussy', 'scrotum', 'sex', 'shit', 'slut', 'smegma', 'spunk', 'twat', 'vagina', 'wank',
             'whore']
profanity_regex = re.compile(r'(' + '|'.join(profanity) + r')', re.IGNORECASE)

date_include_regex = re.compile(r'(' + '|'.join(dates_include) + r')', re.IGNORECASE)
date_exclude_regex = re.compile(r'^(' + '|'.join(dates_dont_include) + r')', re.IGNORECASE)

time_regex = re.compile(r'\d{1,2}(?:(?:am|pm)|(?::\d{1,2})(?:am|pm)?)', re.IGNORECASE)

#### PULL LEGISLATORS IN OFFICE
sunlight.config.API_KEY = 'thisisakey'
legislators = congress.all_legislators_in_office()

twitter_legs = []
leg_names = []

#### CREATE NAMES AND TWITTER HANDLES TO QUERY INCOMING DATA
for leg in legislators:
    if leg.get('twitter_id', None):
        twitter_legs.append(leg.get('twitter_id', None))

    name1 = leg.get('first_name', None) + ' ' + leg.get('last_name', None)
    name2 = leg.get('title', None) + ' ' + leg.get('last_name', None)
    name3 = leg.get('title', None) + ' ' + leg.get('first_name', None) + ' ' + leg.get('last_name', None)
    if leg.get('title', None) == 'Sen':
        name4 = 'Senator ' + leg.get('last_name', None)
        name5 = 'Senator ' + leg.get('first_name', None) + ' ' + leg.get('last_name', None)
        name6 = ''
        name7 = ''
    elif leg.get('title', None) == 'Rep':
        name4 = 'Representative ' + leg.get('last_name', None)
        name5 = 'Representative ' + leg.get('first_name', None) + ' ' + leg.get('last_name', None)
        if leg.get('gender', None) == 'M':
            name6 = 'Congressman ' + leg.get('last_name', None)
            name7 = 'Congressman ' + leg.get('first_name', None) + ' ' + leg.get('last_name', None)
        elif leg.get('gender', None) == 'F':
            name6 = 'Congresswoman ' + leg.get('last_name', None)
            name7 = 'Congresswoman ' + leg.get('first_name', None) + ' ' + leg.get('last_name', None)
        else:
            name6 = ''
            name7 = ''
    else:
        name3 = ''
        name4 = ''
        name5 = ''
        name6 = ''
        name7 = ''

    leg_names.append(name1)
    leg_names.append(name2)
    leg_names.append(name3)
    leg_names.append(name4)
    leg_names.append(name5)
    leg_names.append(name6)
    leg_names.append(name7)

leg_names = list(set(leg_names))

leg_name_regex = re.compile(r'(' + '|'.join(leg_names[1:]) + r')', re.IGNORECASE)
leg_twitter_regex = re.compile(r'(' + '|'.join(twitter_legs) + r')', re.IGNORECASE)
