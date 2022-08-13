#!/usr/bin/env bash

# Copyright 2020 The Tekton Authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# Generate a fresh TEP number
# Requires curl, jq and gnu grep

set -o errexit
set -o nounset
set -o pipefail

# Obtain the list of TEPs from the repo + the list of open PRs
# whose title starts with TEP-NNNN
LAST_TEP=$(
  {
      curl https://api.github.com/repos/tektoncd/community/pulls 2>/dev/null | \
      jq -r '.[] | select(.state == "open") | .title ' | grep -oP 'TEP-[0-9]{4}' | cut -d'-' -f2 & \
      ls teps/ | grep -oP '[0-9]{4}';
  } | sort | tail -1)

printf "%04g" "$((10#$LAST_TEP + 1))"