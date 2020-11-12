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

# This scripts provide automation for the TEPs

from datetime import date
import json
import logging
import os
import re
import sys
from urllib import parse
from urllib import request

import chevron
import click

LOCAL_TEP_FOLDER = os.path.normpath(
    os.path.join(os.path.dirname(
        os.path.abspath(__file__)), '..'))
TEP_TEMPLATE = os.path.normpath(
    os.path.join(os.path.dirname(
        os.path.abspath(__file__)), 'tep-template.md.mustache'))

README_TEMPLATE = 'README.md.mustache'
README = 'README.md'
PR_URL = 'https://api.github.com/repos/tektoncd/community/pulls'
PR_HEADER = {'Accept': 'application/vnd.github.v3.full+json',
             'User-Agent': 'tekton-teps-client'}

# Header and body matches
RE_MATCHERS = {
    'title': re.compile(r'^title: (.+)$'),
    'status': re.compile(r'^status: ([a-zA-Z]+)$'),
    'created': re.compile(r'^creation-date: ([0-9\-\./]+)$'),
    'lastupdated': re.compile(r'^last-updated: ([0-9\-\./]+)$'),
    'number': re.compile(r'^# (TEP-[0-9]{4}): .*$')
}

# File and body matches
RE_TEP_NUMBER_FILENAME = re.compile(r'([0-9]{4})-.*.md')
RE_TEP_NONUMBER_FILENAME = re.compile(r'([A-Za-z]{4})-.*.md')
RE_TEP_NUMBER_PR = re.compile(r'TEP[ -]([0-9]{4})')

EXCLUDED_FILENAMES = set(['README.md',
                          'README.md.mustache',
                          'OWNERS'])

class InvalidTep(Exception):
    pass


class ValidationErrors(Exception):

    def __init__(self, errors):
        self.errors = errors
        super().__init__()

    def __str__(self):
        return '\n'.join([str(e) for e in self.errors])


def read_tep(tep_io, ignore_errors=False):
    """ Read a TEP and validate its format

    :param tep: a TextIO with the TEP content and a name
    :param ignore_errors: return a tep dict even in case of errors
    :returns:  a tuple (dict, list). If the tep is not valid, and
      ignore_errors==True, the list includes all Errors encountered.
    """
    issues = []

    filename = os.path.normpath(tep_io.name)
    _, tep_name = os.path.split(filename)
    tep_match = RE_TEP_NUMBER_FILENAME.match(tep_name)
    tep_file_number = None
    if not tep_match:
        issues.append(InvalidTep(
            f'TEP filenames should match /^[0-9]{4}-/. Found: {tep_name}'))
    else:
        # Get a TEP number from the files name
        tep_file_number = int(tep_match.groups()[0])

    tep = dict(link = tep_name)
    for i, line in enumerate(tep_io):
        # With one author, the title should be in L10
        # Allow for a long list of authors and some padding
        if i > 30:
            break
        # Try to match with all expected fields on this line
        for k, regexp in RE_MATCHERS.items():
            _match = regexp.match(line)
            if _match:
                # If we already found this, log a warning
                # and ignore the new value
                if tep.get(k):
                    issues.append(
                        InvalidTep(f'{key} found more than once in {filename}'))
                else:
                    tep[k] = _match.groups()[0]
                # If we had a match, continue on the next line
                break

    # Some post-processing to handle missing fields
    tep_number = tep.get('number')
    tep_file_number = f'TEP-{tep_file_number:04d}' if tep_file_number is not None else 'TEP-XXXX'
    if not tep_number:
        issues.append(
            InvalidTep(f'No TEP number title (# TEP-NNNN) in {filename}'))
        tep['number'] = tep_file_number
    elif tep_file_number != tep_number:
        issues.append(InvalidTep(
            f'TEP number {tep_file_number} from filename does '
            f'not match TEP number {tep_number} from title '
            f'(# TEP-NNNN) in {filename}'))
    # Set last updated to creation date if missing
    if not tep.get('lastupdated'):
        tep['lastupdated'] = tep.get('created')

    if issues and not ignore_errors:
        raise ValidationErrors(issues)

    return tep, issues


def tep_from_file(tep_filename, ignore_errors=False):
    """ returns a TEP dict for valid input files or None """
    with open(tep_filename, 'r') as tep_file:
        tep, issues = read_tep(tep_file, ignore_errors=ignore_errors)
    if issues:
        logging.warning(f'{issues}')
    return tep


def teps_in_folder(teps_folder):
    return [f for f in os.listdir(LOCAL_TEP_FOLDER) if os.path.isfile(
        os.path.join(LOCAL_TEP_FOLDER, f)) and f not in EXCLUDED_FILENAMES]


def next_tep_number(teps_folder):
    tep_files = teps_in_folder(teps_folder)
    tep_numbers = set()
    # Get all tep numbers from local files
    for tep_file in tep_files:
        tep = tep_from_file(os.path.join(LOCAL_TEP_FOLDER, tep_file),
                            ignore_errors=True)
        if tep:
            tep_numbers.add(tep['number'])
    # Get all tep numbers from open PRs
    # Assuming the PR title starts with TEP-
    prs_request = request.Request(PR_URL, headers=PR_HEADER)
    with request.urlopen(prs_request) as prs_response:
        prs = json.loads(prs_response.read())
    for pr in prs:
        title = pr['title']
        match = RE_TEP_NUMBER_PR.match(title)
        if match:
            number = match.groups()[0]
            tep_numbers.add(f'TEP-{number}')
    for tep_number in sorted(tep_numbers, reverse=True):
        try:
            last = int(tep_number.split('-')[1])
            return last+1
        except ValueError:
            continue
    return 1


@click.group()
def teps():
    pass

@teps.command()
@click.option('--teps-folder', default=LOCAL_TEP_FOLDER,
              help='the folder that contains the TEP files')
def table(teps_folder):
    if not os.path.isdir(teps_folder):
        logging.error(f'Invalid TEP folder {teps_folder}')
        sys.exit(1)
    teps = dict(teps = [])
    tep_files = teps_in_folder(teps_folder)
    for tep_file in tep_files:
        tep = tep_from_file(os.path.join(LOCAL_TEP_FOLDER, tep_file),
                            ignore_errors=True)
        if tep:
            teps['teps'].append(tep)

    # Sort by TEP number
    teps['teps'] = sorted(teps['teps'], key=lambda k: k['number'])
    with open(os.path.join(LOCAL_TEP_FOLDER, README_TEMPLATE), 'r') as template:
        with open(os.path.join(LOCAL_TEP_FOLDER, README), 'w+') as readme:
            readme.write(chevron.render(template, teps))

@teps.command()
@click.option('--teps-folder', default=LOCAL_TEP_FOLDER,
              help='the folder that contains the TEP files')
def validate(teps_folder):
    if not os.path.isdir(teps_folder):
        logging.error(f'Invalid TEP folder {teps_folder}')
        sys.exit(1)
    errors =[]
    tep_numbers = set()
    tep_files = teps_in_folder(teps_folder)

    for tep_file in tep_files:
        try:
            tep = tep_from_file(os.path.join(LOCAL_TEP_FOLDER, tep_file))
            if (number := tep.get('number', '')) in tep_numbers:
                errors.append(InvalidTep(f'{tep_file} uses {number} which was already in use'))
        except ValidationErrors as ve:
            errors.append(ve)
    if errors:
        logging.error('\n'.join([str(e) for e in errors]))
        sys.exit(1)


@teps.command()
@click.option('--teps-folder', default=LOCAL_TEP_FOLDER,
              help='the folder that contains the TEP files')
@click.option('--title', '-t',
              help='the title for the TEP in a few words')
@click.option('--author', '-a', multiple=True,
              help='the title for the TEP in a few words')
def new(teps_folder, title, author):
    if not os.path.isdir(teps_folder):
        logging.error(f'Invalid TEP folder {teps_folder}')
        sys.exit(1)
    tep_number = next_tep_number(teps_folder)
    title_slug = "".join(x for x in title if x.isalnum() or x == ' ')
    title_slug = title_slug.replace(' ', '-')
    tep_filename = f'{tep_number:04d}-{title_slug}.md'
    tep = dict(title=title, authors=author,
               created=str(date.today()),
               lastupdated=str(date.today()),
               status='proposed',
               number=f'TEP-{tep_number}')
    with open(TEP_TEMPLATE, 'r') as template:
        with open(os.path.join(LOCAL_TEP_FOLDER, tep_filename), 'w+') as new_tep:
            new_tep.write(chevron.render(template, tep))
    print(f'{os.path.join(LOCAL_TEP_FOLDER, tep_filename)}')


if __name__ == '__main__':
    teps()
