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
from ruamel.yaml import YAML, YAMLError

LOCAL_TEP_FOLDER = os.path.normpath(
    os.path.join(os.path.dirname(
        os.path.abspath(__file__)), '..'))
TEP_TEMPLATE = os.path.normpath(
    os.path.join(os.path.dirname(
        os.path.abspath(__file__)), 'tep-template.md.template'))

README_TEMPLATE = 'README.md.mustache'
README = 'README.md'
PR_URL = 'https://api.github.com/repos/tektoncd/community/pulls'
PR_HEADER = {'Accept': 'application/vnd.github.v3.full+json',
             'User-Agent': 'tekton-teps-client'}

# File and body matches
RE_TEP_NUMBER_TITLE = re.compile(r'^# (TEP-[0-9]{4}): .*$')
RE_TEP_NUMBER_FILENAME = re.compile(r'([0-9]{4})-.*.md')
RE_TEP_NONUMBER_FILENAME = re.compile(r'([A-Za-z]{4})-.*.md')
RE_TEP_4ALPHANUM_FILENAME = re.compile(r'[A-Za-z0-9]{4}-(.*.md)')
RE_TEP_NUMBER_PR = re.compile(r'TEP[ -]([0-9]{4})')
YAML_SEPARATOR = '---\n'

REQUIRED_FIELDS = ['title', 'authors', 'creation-date', 'status']
EXCLUDED_FILENAMES = set(['README.md',
                          'README.md.mustache',
                          'OWNERS'])

class InvalidTep(Exception):
    pass


class InvalidTepNumber(InvalidTep):
    """ InvalidTepNumber TEP Number

    This exception means something related to TEP numbers
    is wrong. Either that the number in the filename
    does not match the inside the TEP, or there is no number
    in the filename or in the content.
    """
    pass


class ValidationErrors(Exception):

    def __init__(self, errors):
        self.errors = errors
        super().__init__()

    def __str__(self):
        return '\n'.join([str(e) for e in self.errors])


def write_tep_header(tep, tep_io):
    # Build the header dict
    tep_header = {
        'status': tep['status'],
        'title': tep['title'],
        'creation-date': tep['creation-date'],
        'last-updated': tep.get('last-updated', tep['creation-date'])
    }
    tep_header['authors'] = [f'@{a}' for a in tep['authors']]
    # First write the YAML header
    tep_io.write(YAML_SEPARATOR)
    YAML().dump(tep_header, tep_io)
    tep_io.write(YAML_SEPARATOR)
    # Then write the title
    tep_number = int(tep["number"])
    tep_io.write(f'\n# TEP-{tep_number:04d}: {tep_header["title"]}\n')


def read_tep(tep_io, with_body=True, ignore_errors=False):
    """ Read a TEP and validate its format

    :param tep: a TextIO with the TEP content and a name
    :param with_body: whether to return the body
    :param ignore_errors: return a tep dict even in case of errors
    :returns:  a tuple (header, body, list). If the tep is not valid, and
      ignore_errors==True, the list includes all Errors encountered.
    """
    issues = []

    filename = os.path.normpath(tep_io.name)
    _, tep_name = os.path.split(filename)
    tep_match = RE_TEP_NUMBER_FILENAME.match(tep_name)
    tep_file_number = None
    if not tep_match:
        issues.append(InvalidTepNumber(
            f'TEP filenames should match /^[0-9]{4}-/. Found: {tep_name}'))
    else:
        # Get a TEP number from the files name
        tep_file_number = int(tep_match.groups()[0])

    tep = dict(link = tep_name)
    section = ''
    header = []
    body = ''
    for i, line in enumerate(tep_io):
        # Try to match with all expected fields on this line
        if line == YAML_SEPARATOR and section == '':
            section = 'header'
        elif line != YAML_SEPARATOR and section == 'header':
            header.append(line)
        elif line == YAML_SEPARATOR and section == 'header':
            section = 'body'
            try:
                tep.update(YAML().load('\n'.join(header)))
            except YAMLError as ye:
                issues.append(InvalidTep(ye))
        if section == 'body':
            _match = RE_TEP_NUMBER_TITLE.match(line)
            if _match:
                key = 'number'
                if tep.get(key):
                    issues.append(
                        InvalidTepNumber(f'"{key}" found more than once in {filename}'))
                else:
                    tep[key] = _match.groups()[0]
            else:
                if with_body:
                    body += f'{line}'

    # Some post-processing to handle missing fields
    tep_number = tep.get('number')
    tep_file_number = f'TEP-{tep_file_number:04d}' if tep_file_number is not None else 'TEP-XXXX'
    if not tep_number:
        issues.append(
            InvalidTepNumber(f'No TEP number title (# TEP-NNNN) in {filename}'))
        tep['number'] = tep_file_number
    elif tep_file_number != tep_number:
        issues.append(InvalidTepNumber(
            f'TEP number {tep_file_number} from filename does '
            f'not match TEP number {tep_number} from title '
            f'(# TEP-NNNN) in {filename}'))
    # Set last updated to creation date if missing
    if not tep.get('last-updated'):
        tep['last-updated'] = tep.get('creation-date')

    if issues and not ignore_errors:
        raise ValidationErrors(issues)

    return tep, body, issues


def tep_from_file(tep_filename, with_body):
    """ returns a TEP dict for valid input files or None """
    with open(tep_filename, 'r') as tep_file:
        tep, body, _ = read_tep(
            tep_file, ignore_errors=False, with_body=with_body)
    return tep, body


def safe_tep_from_file(tep_filename):
    """ returns a TEP dict for valid input files or None """
    with open(tep_filename, 'r') as tep_file:
        header, _, issues = read_tep(
            tep_file, ignore_errors=True, with_body=False)
    if issues:
        logging.warning(f'{issues}')
    return header


def teps_in_folder(teps_folder):
    return [f for f in os.listdir(teps_folder) if os.path.isfile(
        os.path.join(teps_folder, f)) and f not in EXCLUDED_FILENAMES]


def next_tep_number(teps_folder):
    tep_files = teps_in_folder(teps_folder)
    tep_numbers = set()
    # Get all tep numbers from local files
    for tep_file in tep_files:
        tep = safe_tep_from_file(os.path.join(teps_folder, tep_file))
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


def generate_tep_table(teps_folder):
    teps = dict(teps = [])
    tep_files = teps_in_folder(teps_folder)
    for tep_file in tep_files:
        tep = safe_tep_from_file(os.path.join(teps_folder, tep_file))
        if tep:
            # mustache doesn't link variables with a dash
            tep['lastupdated'] = tep['last-updated']
            teps['teps'].append(tep)

    # Sort by TEP number
    teps['teps'] = sorted(teps['teps'], key=lambda k: k['number'])
    with open(os.path.join(teps_folder, README_TEMPLATE), 'r') as template:
        with open(os.path.join(teps_folder, README), 'w+') as readme:
            readme.write(chevron.render(template, teps))


@click.group()
def teps():
    pass


@teps.command()
@click.option('--teps-folder', default=LOCAL_TEP_FOLDER,
              help='the folder that contains the TEP files')
def table(teps_folder):
    """ Generate a table of TEPs from the teps in a folder """
    if not os.path.isdir(teps_folder):
        logging.error(f'Invalid TEP folder {teps_folder}: folder could not be found')
        sys.exit(1)
    generate_tep_table(teps_folder)


@teps.command()
@click.option('--teps-folder', default=LOCAL_TEP_FOLDER,
              help='the folder that contains the TEP files')
def validate(teps_folder):
    """ Validate all the TEPs in a tep """
    if not os.path.isdir(teps_folder):
        logging.error(f'Invalid TEP folder {teps_folder}')
        sys.exit(1)
    errors =[]
    tep_numbers = set()
    tep_files = teps_in_folder(teps_folder)

    for tep_file in tep_files:
        try:
            tep, _ = tep_from_file(
                os.path.join(teps_folder, tep_file), with_body=False)
            for field in REQUIRED_FIELDS:
                if tep.get(field, None) is None:
                    errors.append(InvalidTep(f'{field} missing in {tep_file}'))
            if (number := tep.get('number', '')) in tep_numbers:
                errors.append(InvalidTepNumber(f'{tep_file} uses {number} which was already in use'))
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
@click.option('--update-table/--no-update-table', default=True,
              help='whether to refresh the table of TEPs')
def new(teps_folder, title, author, update_table):
    """ Create a new TEP with a new valid number from the template """
    if not os.path.isdir(teps_folder):
        logging.error(f'Invalid TEP folder {teps_folder}')
        sys.exit(1)
    tep_number = next_tep_number(teps_folder)
    title_slug = "".join(x for x in title if x.isalnum() or x == ' ')
    title_slug = title_slug.replace(' ', '-').lower()
    tep_filename = f'{tep_number:04d}-{title_slug}.md'
    tep = dict(title=title, authors=author,
               status='proposed',
               number=tep_number)
    tep['creation-date'] = str(date.today())
    tep['last-updated'] =str(date.today())
    with open(os.path.join(teps_folder, tep_filename), 'w+') as new_tep:
        write_tep_header(tep, new_tep)
        with open(TEP_TEMPLATE, 'r') as template:
            new_tep.write(template.read())

    # By default, regenerate the TEP folder
    if update_table:
        generate_tep_table(teps_folder)

    # Return git help to execute
    print(f'\n\nTo stage the new TEP please run:\n\n'
          f'git status    # optional\n'
          f'git add {os.path.join(teps_folder, tep_filename)}\n')


@teps.command()
@click.option('--teps-folder', default=LOCAL_TEP_FOLDER,
              help='the folder that contains the TEP files')
@click.option('--filename', '-f', default=None,
              help='the filename of the TEP to refresh')
@click.option('--update-table/--no-update-table', default=True,
              help='whether to refresh the table of TEPs')
def renumber(teps_folder, filename, update_table):
    """ Obtain a fresh TEP number and refresh the TEP and TEPs table """
    if not os.path.isdir(teps_folder):
        logging.error(f'Invalid TEP folder {teps_folder}')
        sys.exit(1)

    # Load the TEP header first
    source_filename = os.path.join(teps_folder, filename)
    try:
        tep, body = tep_from_file(source_filename, with_body=True)
    except ValidationErrors as ve:
        # If validation errors are related to the TEP number
        # we may be able to fix them
        non_number_errors = [e for e in ve is not isinstance(ve, InvalidTepNumber)]
        logging.warning(f'Validation issues found. Please fix them '
                        f'before updating the PR: {non_number_errors}')
        if len(ve) == len(non_number_errors):
            logging.warning('No number issues found, refreshing anyways')

    # Obtain a new TEP number
    tep_number = next_tep_number(teps_folder)
    tep['number'] = tep_number

    # Build the target TEP filename
    filename_match = RE_TEP_4ALPHANUM_FILENAME.match(filename)
    base_filename = filename
    if filename_match:
        base_filename = filename_match.groups()[0]
    target_filename = f'{tep_number:04d}-{base_filename}'
    target_filename = os.path.join(teps_folder, target_filename)

    with open(target_filename, 'w+') as target:
        # First re-write the header that was parsed
        write_tep_header(tep, target)
        # Write the parsed body
        target.write(body)

    logging.info(f'New TEP {target_filename} created')

    # By default, regenerate the TEP folder
    if update_table:
        generate_tep_table(teps_folder)

    # Return git commands to execute
    print(f'\n\nTo complete the PR please run:\n\n'
          f'git status    # optional\n'
          f'git diff      # optional\n'
          f'git add {target_filename}\n'
          f'git rm {source_filename}\n'
          f'git add -u\n'
          f'git commit --amend\n')


if __name__ == '__main__':
    teps()
