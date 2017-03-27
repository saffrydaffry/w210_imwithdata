import os
import sys

from setuptools import setup

if sys.version_info[0] != 3:
    sys.exit("Python 3 required")

version = os.environ['BUILD_NUMBER'] if 'BUILD_NUMBER' in os.environ else '1.0'

setup(name='imwithdata',
      version=version,
      description='Scripts associated with ETL for Rzst.us',
      url='rzst.us',
      author='Safyre Anderson',
      author_email='safyre@berkeley.edu',
      install_requires=[
          'elasticsearch==5.2.0',
          'PyMySQL==0.7.9',
          'sqlalchemy=1.1.6',
          'tqdm==4.11.2',
          'boto3==1.4.3',
          'retrying==1.3.3',
          'beautifulsoup4==4.5.3',
      ],
      setup_requires=[
          'pandas=0.19.2=np112py35_1',
      ],
      tests_require=[
          'pytest==2.9.2',
      ],
      packages=['imwithdata', 'imwithdata.es_etl'],
      zip_safe=False
      )