import argparse
import boto3
import pandas as pd

from datetime import (
    datetime,
    timedelta
)
from imwithdata.s3_etl import (
    twitter,
    meetup,
    legislators,
    townhalls,
    conn_rzst_sql
)
from imwithdata.utils import (
    df_from_s3
)

# --- Globals --- #
doc_types = ["meetup", "twitter"]
BUCKET = "mids-capstone-rzst"
S3_FILE = "es_data.csv"
PREFIX = "es_staging"


# --- Switch --- #
put_rzst_doc = {
    'meetup': meetup,
    'twitter': twitter,
    'legislators': legislators,
    'townhalls': townhalls
}


def get_s3_key(doc_type, date):
    """Generate a key to load data."""
    return "/".join([PREFIX, date, doc_type, S3_FILE])


def s3_to_sql(args):
    print("Pulling data from s3...")
    s3 = boto3.client("s3", "us-west-2")
    date = args.date
    conn = conn_rzst_sql()

    for doc_type in doc_types:
        print("Extracting %s data: " % doc_type)
        s3_key = get_s3_key(doc_type, date)
        print("From %s" % s3_key)
        data = df_from_s3(bucket=BUCKET, s3_client=s3, key=s3_key)
        final_data = put_rzst_doc[doc_type](data, conn)



def csv_to_sql(args):
    """Upload a csv file as pandas dataframe
    Load data to s3
    
    :param args: 
    :return: 
    """
    doc_type = args.type
    data = pd.read_csv(args.infile)
    conn = conn_rzst_sql()
    put_rzst_doc[doc_type](data, conn)


def main():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(help="subcomand help")
    # S3 input
    parser_s3 = subparsers.add_parser('s3', help="Data source in s3. Only processes twitter, meetup data")
    parser_s3.add_argument("--date", type=str, nargs="?",
                           default=(datetime.today() - timedelta(days=1)).date.isoformat(),
                           help="Date of data to pull from s3. Expected format is %y.%m.%d")
    parser_s3.set_defaults(func=s3_to_sql)

    # CSV input
    parser_csv = subparsers.add_parser('csv', help="Full path for csv.")
    parser_csv.add_argument("--infile", type=str,
                            help="Full file path of .csv file")
    parser_csv.add_argument("--type", type=str,
                            help="Document type to parse")
    parser_csv.set_defaults(func=csv_to_sql)

    # Run the function according to the subparser action called.
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()


