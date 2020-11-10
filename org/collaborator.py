#!/usr/bin/env python

# Copyright 2020 The Tekton Authors
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# This script helps synchronize contents from their respective sources of
# truth (usually GitHub repositories of each Tekton
# components, such as tektoncd/pipelines) to tektoncd/website.

# This script builds a table collaborator for the various repos in the
# Tekton CD org. The list of collaborators is used to create configuration
# for collaborator teams on GitHub side, which are then sync'ed to GitHub
# via the existing peribolos infrastructure.

# Collaborators are selected by searching for anyone in the Tekton org
# that has contributed at least 5 commits (ever) to the specific repo.
# This script is meant as a one-off to setup the initial teams. Further
# edits to the teams will be managed by PRs to the org/org.yaml config.

import logging
import os

import github
from ruamel.yaml import YAML


ORG_CONFIG = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'org.yaml')
GOVERNANCE_TEAM = ['abayer', 'afrittoli', 'bobcatfish', 'ImJasonH', 'vdemeester']

def get_contributors_maintainers(github_token):
    g = github.Github(github_token)

    # Get the ORG members
    tektoncd = g.get_organization("tektoncd")
    members = [x for x in tektoncd.get_members()]
    members_ids = [x.node_id for x in members]

    # Get the list of repos
    repos = [x for x in tektoncd.get_repos() if x.name != '.github']

    # Get stats/contributors for each repo with 5+ commits
    contributors = {}
    maintainers = set()
    for repo in repos:
        logging.info(f'Searching contributors to {repo.name}')
        # Get the list of contributors that have 5+ commits and are members
        contributors[repo.name] = set([
            x.author.login for x in repo.get_stats_contributors()
            if x.total >= 5 and x.author.node_id in members_ids])

        # Get the list of maintainers and merge them to a set
        logging.info(f'Searching maintainers to {repo.name}')
        _maintainers = [x for x in repo.get_teams()
            if x.name.endswith('.maintainers')]
        if len(_maintainers) > 0:
            maintainers.update([x.login for x in _maintainers[0].get_members()])

    # Any maintainer on any repo is allowed to lgtm on community (for TEPs)
    contributors['community'] = maintainers

    return contributors


def update_collaborator_teams(contributors):
    yaml = YAML()

    # Load the YAML config
    logging.info(f'Loading org configuration from {ORG_CONFIG}')
    with open(ORG_CONFIG, 'r') as org_config_file:
        org_config = yaml.load(org_config_file)

    # Update the config with collaborator teams
    for repo, collaborators in contributors.items():
        repo_name = repo if repo != 'pipeline' else 'core'
        team_name = f'{repo_name}.collaborators'
        # The least maintainers does not matter too much, because we're
        # maintaining the configuration via periobolos and not via GitHub
        # Setting the governance team as default as a backup.
        maintainers = [m for m in GOVERNANCE_TEAM if m not in collaborators] or ['bobcatfish']
        team = dict(
            description=f'The {repo_name} collaborators',
            maintainers=maintainers,
            members = [c for c in collaborators if c not in maintainers],
            privacy = 'closed',
            repos = {repo: 'read'}
        )
        logging.info(f'Adding team {team_name}')
        org_config['orgs']['tektoncd']['teams'][team_name] = team

    # Save the config back to disk
    logging.info(f'Saving org configuration to {ORG_CONFIG}')
    with open(ORG_CONFIG, 'w') as org_config_file:
        yaml.dump(org_config, org_config_file)

if __name__ == '__main__':
    github_token = os.getenv('GITHUB_TOKEN')
    if not github_token:
        logging.error('GITHUB_TOKEN must be set')
        sys.exit(1)
    contributors = get_contributors_maintainers(github_token)
    update_collaborator_teams(contributors)
