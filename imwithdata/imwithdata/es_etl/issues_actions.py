#!/usr/bin/env python3
"""Lists that keep track of issues, actions, keywords

"""

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
                       "give",
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
                          '@SierraClub'
                          ]
              }
