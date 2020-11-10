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

import json
import logging
import os
import re
from urllib import parse

import chevron

LOCAL_TEP_FOLDER = os.path.join(os.path.dirname(
    os.path.abspath(__file__)), '../teps')
README_TEMPLATE = 'README.md.mustache'
README = 'README.md'

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


def tep_from_file(tep_filename):
    """ returns a TEP dict for valid input files or None """

    # Only use files that use the TEPs filename format
    # that matches NNNN-some-name.md
    filename = os.path.basename(tep_filename)
    tep_match = RE_TEP_NUMBER_FILENAME.match(filename)
    if not tep_match:
        tep_match = RE_TEP_NONUMBER_FILENAME.match(filename)
        if not tep_match:
            return None

    # Start with the TEP link
    tep = dict(link = filename)

    # Try to get a TEP number from the files name
    # and fallback to none otherwise
    tep_file_number = tep_match.groups()[0]
    try:
        int(tep_file_number)
        tep_file_number = 'TEP-' + tep_file_number
    except ValueError:
        tep_file_number = 'TEP-NNNN'

    with open(tep_filename, 'r') as tep_file:
        for i, line in enumerate(tep_file):
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
                        logging.warning(
                            f'{key} found more than once in {filename}')
                    else:
                        tep[k] = _match.groups()[0]
                    # If we had a match, continue on the next line
                    break

    # Some post-processing to handle missing fields
    tep_number = tep.get('number')
    if not tep_number:
        logging.warning(f'No TEP number title (# TEP-NNNN) in {filename}')
        tep['number'] = tep_file_number
    elif tep_file_number != tep_number:
        logging.warning((f'TEP number {tep_file_number} from filename does '
                         f'not match TEP number {tep_number} from title '
                         f'(# TEP-NNNN) in {filename}'))
    # Set last updated to creation date if missing
    if not tep.get('lastupdated'):
        tep['lastupdated'] = tep.get('created')

    return tep


def main():
    teps = dict(teps = [])
    tep_files = [f for f in os.listdir(LOCAL_TEP_FOLDER) if os.path.isfile(
        os.path.join(LOCAL_TEP_FOLDER, f))]
    for tep_file in tep_files:
        tep = tep_from_file(os.path.join(LOCAL_TEP_FOLDER, tep_file))
        if tep:
            teps['teps'].append(tep)

    # Sort by TEP number
    teps['teps'] = sorted(teps['teps'], key=lambda k: k['number'])
    with open(os.path.join(LOCAL_TEP_FOLDER, README_TEMPLATE), 'r') as template:
        with open(os.path.join(LOCAL_TEP_FOLDER, README), 'w+') as readme:
            readme.write(chevron.render(template, teps))


if __name__ == '__main__':
    main()
