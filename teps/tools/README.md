# `teps` automation tool

The `teps.py` tool implements automation for TEPs.
The tool support a few different commands, as well as online help:

```shell
$ ./teps.py
Usage: teps.py [OPTIONS] COMMAND [ARGS]...

Options:
  --help  Show this message and exit.

Commands:
  new       Create a new TEP with a new valid number from the template
  renumber  Obtain a fresh TEP number and refresh the TEP and TEPs table
  table     Generate a table of TEPs from the teps in a folder
  validate  Validate all the TEPs in a tep
```

## Installation

The `teps.py` tool is a python script, it requires python 3.6+ to run.
To install its dependencies and execute the script, run the following
commands from the root of the tektoncd/community repo:

```shell
# Create a Virtual Environment
python3 -m venv .venv
. .venv/bin/activate

# Install the requirements
pip3 install -r ./teps/tools/requirements.txt

# Test the script
./teps/tools/teps.py
```

## `new`

The new command creates a new TEP from the template.
It allocates a new TEP number based on existing TEPs in the repo as well as PRs with title 'TEP[ -]NNNN'. It automatically sets title, authors,
dates and status based on the inputs provided.

```shell
$ ./teps.py new --help
Usage: teps.py new [OPTIONS]

  Create a new TEP with a new valid number from the template

Options:
  --teps-folder TEXT              the folder that contains the TEP files
  -t, --title TEXT                the title for the TEP in a few words
  -a, --author TEXT               the title for the TEP in a few words
  --update-table / --no-update-table
                                  whether to refresh the table of TEPs
  --help                          Show this message and exit.
```

Example:

```shell
$ ./teps.py new --title "My brand new tep" -a "tizio" -a "caio" -a "sempronio"

/go/src/github.com/tektoncd/community/teps/0034-My-brand-new-tep.md
```

The header of the new TEP will look like:

```yaml
---
title: My brand new tep
authors:
  - @tizio
  - @caio
  - @sempronio
creation-date: 2020-11-12
last-updated: 2020-11-12
status: proposed
---

# TEP-34: My brand new tep
```

## `table`

The `table` command updates the TEP table in the README.md from the list of TEPs available in the repository:

```shell
$ ./teps.py table --help
Usage: teps.py table [OPTIONS]

  Generate a table of TEPs from the teps in a folder

Options:
  --teps-folder TEXT  the folder that contains the TEP files
  --help              Show this message and exit.
  ```

The `table` command also checks if the TEPs are well formed. If not it will log a warning but still exit with a successful exit code.

## `validate`

The `validate` command checks if the TEPs are all well formed. If not it prints the errors it encountered and exists with a failure exit code.
The `validate` command attempts to parse all TEP files, regardless of errors, to collect as many issues as possible before exiting:

```shell
$ ./teps.py validate --help
Usage: teps.py validate [OPTIONS]

  Validate all the TEPs in a tep

Options:
  --teps-folder TEXT  the folder that contains the TEP files
  --help              Show this message and exit.
```

Example:

```shell
$ ./teps.py validate
ERROR:root:TEP filenames should match /^[0-9]4-/. Found: XXXX-workspace-paths.md
No TEP number title (# TEP-NNNN) in /System/Volumes/Data/go/src/github.com/tektoncd/community/teps/XXXX-workspace-paths.md
No TEP number title (# TEP-NNNN) in /System/Volumes/Data/go/src/github.com/tektoncd/community/teps/0033-My-brand-new-tep.md
No TEP number title (# TEP-NNNN) in /System/Volumes/Data/go/src/github.com/tektoncd/community/teps/0034-My-brand-new-tep.md
TEP number TEP-0028 from filename does not match TEP number TEP-0027 from title (# TEP-NNNN) in /System/Volumes/Data/go/src/github.com/tektoncd/community/teps/0028-task-execution-status-at-runtime.md
No TEP number title (# TEP-NNNN) in /System/Volumes/Data/go/src/github.com/tektoncd/community/teps/0032-test-title.md
TEP filenames should match /^[0-9]4-/. Found: XXXX-step-workspaces.md
No TEP number title (# TEP-NNNN) in /System/Volumes/Data/go/src/github.com/tektoncd/community/teps/XXXX-step-workspaces.md
No TEP number title (# TEP-NNNN) in /System/Volumes/Data/go/src/github.com/tektoncd/community/teps/0022-trigger-immutable-input.md

$ echo $?
1
```

## `renumber`

The `renumber` obtains a new number and updates the specified TEP accordingly. This command changes the TEP filename as well as the number in the content. It optionally updates the table of TEPs too.

```shell
$ ./teps.py renumber --help
Usage: teps.py renumber [OPTIONS]

  Obtain a fresh TEP number and refresh the TEP and TEPs table

Options:
  --teps-folder TEXT              the folder that contains the TEP files
  -f, --filename TEXT             the filename of the TEP to refresh
  --update-table / --no-update-table
                                  whether to refresh the table of TEPs
  --help                          Show this message and exit.
```
