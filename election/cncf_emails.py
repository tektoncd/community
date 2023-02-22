#!/usr/bin/env python3

"""cncf_emails.py Extracts github IDs from a CSV and matches them
to emails through a JSON map.

The CVS input file can be obtained from devstats. Clink on the link:
https://tekton.devstats.cd.foundation/d/9/developer-activity-counts-by-repository-group-table?inspect=1&inspectTab=data&viewPanel=1&orgId=1&var-period_name=Last%20year&var-metric=contributions&var-repogroup_name=All&var-country_name=All
and use the download CSV button to download the CSV file.

The script takes the JSON map from https://github.com/cncf/devstats/blob/master/github_users.json,
which is one of the input files used by the CDF for devstats.

The output will be a mapping of the GitHub username to the all email addresses
contained in commits associated with this user in a csv file.

Usage:
  python3 cncf_emails.py --file users.csv
"""
import argparse
import csv
import requests
from typing import List, Dict

import pandas as pd

EMAIL_MAP = "https://github.com/cncf/devstats/raw/master/github_users.json"

if __name__ == '__main__':
  arg_parser = argparse.ArgumentParser(
      description="Try to find email addresses for GitHub usernames")
  arg_parser.add_argument("--file", type=str, required=True,
                          help="A file containing the GitHub usernames to query, separated by a newline")
  arg_parser.add_argument("--csv", type=str, required=False,
                          help="csv file to write with results")
  args = arg_parser.parse_args()

  csvfile = args.csv or "found_emails.csv"
  missingfile = "missing_emails.csv"

  # load data
  users = pd.read_csv(args.file)
  emailmap = pd.read_json(EMAIL_MAP)
  emailmap = emailmap[~emailmap['email'].str.endswith('users.noreply.github.com')]

  # filter eligible users
  eligible = users[users['value'] >= 15]
  found = pd.merge(eligible, emailmap, left_on='name', right_on='login', how='left', indicator=True).query('_merge == "both"').drop(columns='_merge')
  found['email'] = found['email'].str.replace('!', '@')
  missing = pd.merge(eligible, emailmap, left_on='name', right_on='login', how='left', indicator=True).query('_merge == "left_only"').drop(columns='_merge')
  found.to_csv(csvfile, columns=['name_x', 'email'], header=False, index=False)
  missing.to_csv(missingfile, columns=['name_x'], header=False, index=False)
