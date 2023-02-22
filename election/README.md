# Election

This folder holds scripts and other info used for the governing board election.

## Finding eligble voter eamils

Scripts in this folder are used to (approximately) find emails of users that meet
[the eligibility requirements](https://github.com/tektoncd/community/blob/main/governance.md#elections)
so that [links to active elections](https://github.com/tektoncd/community/blob/main/governance.md#election-process)
can be sent to them.

There are two scripts, which look at two different sources to find emails:

* [github_emails.py](./github_emails.py) extracts emails from GitHub activity
* [cncf_emails.py](./cncf_emails.py) uses a CNCF list of emails

Both take [a `.csv` file of users from devstats](#getting-users-from-devstats) as input.

Reconciling the lists and tracking down missing users from this point is manual.

### Getting users from devstats

1. Find eligible github users [using this link](https://tekton.devstats.cd.foundation/d/9/developer-activity-counts-by-repository-group-table?orgId=1&var-period_name=Last%20year&var-metric=contributions&var-repogroup_name=All&var-country_name=All)
2. Export the data as a `.csv` (from the Table title, go to Inspect->Data->Download CSV)

### Running the GitHub script

To run this script you will need [a GitHub OAuth token](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/creating-a-personal-access-token)
to make requests to GitHub (it does not require any specific access).

This script will create a file called `emails.csv` which contains the found emails.

```bash
python3 github_emails.py --file users.csv --token $GITHUB_OAUTH_TOKEN
```

### Running the cncf script

This script will create a file called `found_emails.csv` with the found emails and one called `missing_emails.csv`
with the usernames it couldn't map.

```bash
# you will need to install the pandas library
python3 -m venv ./voters
source ./voters/bin/activate
pip3 install pandas

# run the script
python3 cncf_emails.py --file users.csv
```