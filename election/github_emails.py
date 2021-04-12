#!/usr/bin/env python3

"""get_emails.py queries GitHub for the email addresses to use for usernames.

The script takes a list of GitHub usernames as input (obtained from
https://tekton.devstats.cd.foundation/d/9/developer-activity-counts-by-repository-group-table?orgId=1&var-period_name=Last%20year&var-metric=contributions&var-repogroup_name=All&var-country_name=All)
where each username is separated by a newline,
and for each username, queries GitHub for their recent activity
(https://developer.github.com/v3/activity/events/#list-events-performed-by-a-user).
If they have a PushEvent that will contain the commit(s) and email addresses.

The output will be a mapping of the GitHub username to the all email addresses
contained in commits associated with this user in a csv file.

Usage:
  python3 github_emails.py --file users --token $GITHUB_OAUTH_TOKEN
"""
import argparse
import csv
import requests
from typing import List, Dict


GITHUB_EVENTS_API = "https://api.github.com/users/{}/events"



def read_users(filename: str) -> List[str]:
  with open(filename) as f:
    return [x.strip() for x in f.readlines()]


def query_github(users: List[str], token: str) -> Dict[str, Dict]:
  results = {}
  for user in users:
    print("Getting events for {}".format(user))

    url = GITHUB_EVENTS_API.format(user)
    r = requests.get(url, headers={"Authorization": "token {}".format(token)})
    try:
      r.raise_for_status()
    except requests.exceptions.HTTPError as e:
      print("Error for {}: {}".format(user, e))
    results[user] = r.json()
  return results


def extract_emails(results: Dict[str, Dict]) -> Dict[str, List[str]]:
  emails = {}
  for user, result in results.items():
    emails[user] = set()
    for r in result:
      if "type" in r and r["type"] == "PushEvent":
        # Extract the email from the first commit
        if "payload" in r and "commits" in r["payload"]:
          commits = r["payload"]["commits"]
          if (len(commits) > 0 and "author" in commits[0]
              and "email" in commits[0]["author"]):
            emails[user].add(commits[0]["author"]["email"])
  return emails


def make_csv(csvfile: str, emails: Dict[str, List[str]]) -> None:
  with open(csvfile, 'w') as f:
    w = csv.writer(f, delimiter=',')
    for user, emails in emails.items():
      w.writerow([user] + list(emails))


if __name__ == '__main__':
  arg_parser = argparse.ArgumentParser(
      description="Try to find email addresses for GitHub usernames")
  arg_parser.add_argument("--file", type=str, required=True,
                          help="A file containing the GitHub usernames to query, separated by a newline")
  arg_parser.add_argument("--token", type=str, required=True,
                          help="GitHub oauth token to use when making requests to avoid rate limiting")
  arg_parser.add_argument("--csv", type=str, required=False,
                          help="csv file to write with results")
  args = arg_parser.parse_args()

  csvfile = args.csv or "emails.csv"

  users = read_users(args.file)
  results = query_github(users, args.token)
  emails = extract_emails(results)
  print(emails)
  make_csv(csvfile, emails)

