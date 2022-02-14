# Tekton working group

Most community activity is organized into _working groups_.

Working groups follow the [contributing](./CONTRIBUTING.md) guidelines although
each of these groups may operate a little differently depending on their needs
and workflow.

The working groups generate design docs which are kept in a
[shared drive](./contact.md#shared-drive)
and are available for anyone to read and comment on. The shared drive currently
grants read access to
[tekton-users@](https://groups.google.com/forum/#!forum/tekton-users) and edit
and comment access to the
[tekton-dev@](https://groups.google.com/forum/#!forum/tekton-dev) Google
group.

Additionally, all working groups should hold regular meetings, which should be
added to the
[shared tekton calendar](https://calendar.google.com/calendar?cid=Z29vZ2xlLmNvbV9kM292Y3ZvMXAzMjE5aDk4OTU3M3Y5OGZuc0Bncm91cC5jYWxlbmRhci5nb29nbGUuY29t)
WG leads should have access to be able to create and update events on this
calendar, and should invite tekton-dev@googlegroups.com to working group
meetings.

Recordings are made and posted in the minutes of each meeting.
These docs and the recordings themselves are visible to [all members of our mailing list](#mailing-list).

The current working groups are:

- [General](#general)
- [Triggers](#triggers)
- [CLI](#cli)
- [Documentation](#documentation)
- [Productivity](#productivity)
- [API](#api)
- [Dashboard](#dashboard)
- [Catalog and Hub](#catalog-and-hub)
- [Operator and Deployment](#operator-and-deployment)
- [Chains](#chains)
- [Workflows](#workflows)
- [Pipeline](#pipeline)
- [Governing board / Community](#governing-board--community)
- [Software Supply Chains Security (s3c)](#software-supply-chain-security-s3c)

## General

This is the general working group, where we discuss each project's
update and cross-project subjects. This is also the main working group
to discuss the `tektoncd/pipeline` project.

We altenate between two meeting times, a time that is friendly for Europe + North America
(PST+EST+CEST) and a time that is friendly for Asia + Europe (CEST+IST+CST).

| Artifact                   | Link                       |
| -------------------------- | -------------------------- |
| Forum                      | [tekton-dev@](https://groups.google.com/forum/#!forum/tekton-dev) |
| Slack Channel              | [#pipeline](https://tektoncd.slack.com/messages/pipeline) |
| Meeting Notes              | [Notes](https://docs.google.com/document/d/1rPR7m1Oj0ip3bpd_bcS1sjZyPgGi_g9asF5YrExeESc) |

### Europe + North America

| Artifact                   | Link                       |
| -------------------------- | -------------------------- |
| Community Meeting VC       | [https://meet.google.com/gnx-mwhf-wqt](https://meet.google.com/gnx-mwhf-wqt) |
| Community Meeting Calendar | Wednesdays 9:00am-10:00am PST <br>[Calendar](https://calendar.google.com/event?action=TEMPLATE&tmeid=bjc0aWJqMzVtYm04ZWt2NHJlajJmajdvNGtfMjAxOTA1MjlUMTYwMDAwWiBnb29nbGUuY29tX2Qzb3Zjdm8xcDMyMTloOTg5NTczdjk4Zm5zQGc&tmsrc=google.com_d3ovcvo1p3219h989573v98fns%40group.calendar.google.com&scp=ALL) |

| &nbsp;                                                     | Facilitators    | Company | Profile                                     |
| --------------------------------------------------------   | ----------      | ------- | ---------------------------------------     |
| <img width="30px" src="https://github.com/bobcatfish.png"> | Christie Wilson | Google  | [bobcatfish](https://github.com/bobcatfish) |
| <img width="30px" src="https://github.com/skaegi.png">     | Simon Kaegi     | IBM     | [skaegi](https://github.com/skaegi)         |
| <img width="30px" src="https://github.com/dibyom.png">     | Dibyo Mukherjee | Google  | [dibyom](https://github.com/dibyom)         |
| <img width="30px" src="https://github.com/pritidesai.png"> | Priti Desai     | IBM     | [pritidesai](https://github.com/pritidesai) |
| <img width="30px" src="https://github.com/imjasonh.png">   | Jason Hall      | Red Hat | [imjasonh](https://github.com/imjasonh)     |

### Europe + Asia

| Artifact                   | Link                       |
| -------------------------- | -------------------------- |
| Community Meeting VC       | [meet.google.com/xgi-shbo-mym](https://meet.google.com/xgi-shbo-mym) |
| Community Meeting Calendar | Wednesdays 8:30pm-9:30pm CST <br>[Calendar](https://calendar.google.com/event?action=TEMPLATE&tmeid=M3Rsa2lsdnA5ZGc2aHJ1bGlqdGUzOXFnYjNfMjAyMDAxMjJUMTIzMDAwWiBnb29nbGUuY29tX2Qzb3Zjdm8xcDMyMTloOTg5NTczdjk4Zm5zQGc&tmsrc=google.com_d3ovcvo1p3219h989573v98fns%40group.calendar.google.com&scp=ALL) |

| &nbsp;                                                     | Facilitators      | Company | Profile                                     |
| --------------------------------------------------------   | ----------        | ------- | ---------------------------------------     |
| <img width="30px" src="https://github.com/afrittoli.png">  | Andrea Frittoli   | IBM     | [afrittoli](https://github.com/afrittoli) |
| <img width="30px" src="https://github.com/vdemeester.png"> | Vincent Demeester | Red Hat | [vdemeester](https://github.com/vdemeester) |

## Triggers

This is the [`tektoncd/triggers`](https://github.com/tektoncd/triggers) working group.

| Artifact                   | Link                       |
| -------------------------- | -------------------------- |
| Forum                      | [tekton-dev@](https://groups.google.com/forum/#!forum/tekton-dev) |
| Community Meeting VC       | [https://meet.google.com/oqm-imjh-uzu](https://meet.google.com/oqm-imjh-uzu) |
| Community Meeting Calendar | Wednesdays every week, 11:00p-11:30p EST <br>[Calendar](https://calendar.google.com/event?action=TEMPLATE&tmeid=ZDA3YzZldXZqZ2M1ajBndWVkNzRlNTdzN2ZfMjAyMDExMThUMTYwMDAwWiBnb29nbGUuY29tX2Qzb3Zjdm8xcDMyMTloOTg5NTczdjk4Zm5zQGc&tmsrc=google.com_d3ovcvo1p3219h989573v98fns%40group.calendar.google.com&scp=ALL) |
| Meeting Notes              | [Notes](https://docs.google.com/document/d/16dtgpeNQgpC33gjZEFUqQv-G7QwVDHbuwJQOGmy1l7w/edit) |
| Document Folder            | [Folder](https://drive.google.com/drive/folders/1-UOR-sodtMeYqtUEzVW12nkfJCr7EQRO) |
| Slack Channel              | [#triggers](https://tektoncd.slack.com/messages/triggers) |

| &nbsp;                                                           | Facilitators    | Company     | Profile                                                 |
| --------------------------------------------------------         | ----------      | -------     | ---------------------------------------                 |
| <img width="30px" src="https://github.com/wlynch.png">           | Billy Lynch     | Google      | [wlynch](https://github.com/wlynch)                     |
| <img width="30px" src="https://github.com/dibyom.png">           | Dibyo Mukherjee | Google      | [dibyom](https://github.com/dibyom)                     |
| <img width="30px" src="https://github.com/khrm.png">             | Khurram Baig    | Red Hat     | [khrm](https://github.com/khrm)                         |
| <img width="30px" src="https://github.com/savitaashture.png">    | Savita Asthure  | Red Hat     | [savitaashture](https://github.com/savitaashture)       |

## CLI

This is the [`tektoncd/cli`](https://github.com/tektoncd/cli) working group.

| Artifact                   | Link                       |
| -------------------------- | -------------------------- |
| Forum                      | [tekton-dev@](https://groups.google.com/forum/#!forum/tekton-dev) |
| Community Meeting VC       | [https://meet.google.com/mwj-mfpy-ybk](https://meet.google.com/mwj-mfpy-ybk) |
| Community Meeting Calendar | Tuesdays 08:00a-08:30a EST <br>[Calendar](https://calendar.google.com/event?action=TEMPLATE&tmeid=ZmV1ZmI2dnJjYm9wYWFkaXNxdWJuOWo1bWRfMjAyMDAxMjhUMTMwMDAwWiBnb29nbGUuY29tX2Qzb3Zjdm8xcDMyMTloOTg5NTczdjk4Zm5zQGc&tmsrc=google.com_d3ovcvo1p3219h989573v98fns%40group.calendar.google.com&scp=ALL) |
| Meeting Notes              | [Notes](https://docs.google.com/document/d/1J1LkrmLtMdtdJqFcsyOKsJJc4lEm7YL-97D51PzpHrQ/edit) |
| Document Folder            | [Folder](https://drive.google.com/drive/folders/1FnMx4h8WkeBEo3vYl3w2IAOa-otf_a2j) |
| Slack Channel              | [#cli](https://tektoncd.slack.com/messages/cli) |

| &nbsp;                                                        | Facilitators     | Company | Profile                                           |
| --------------------------------------------------------      | ----------       | ------- | ---------------------------------------           |
| <img width="30px" src="https://github.com/chmouel.png">       | Chmouel Boudjnah | Red Hat | [chmouel](https://github.com/chmouel)             |
| <img width="30px" src="https://github.com/danielhelfand.png"> | Daniel Helfand   | VMware  | [danielhelfand](https://github.com/danielhelfand) |
| <img width="30px" src="https://github.com/pradeepitm12.png">  | Pradeep Kumar    | Red Hat | [pradeepitm12](https://github.com/pradeepitm12)   |
| <img width="30px" src="https://github.com/pgarg.png">         | Piyush Garg      | Red Hat | [piyush-garg](https://github.com/piyush-garg)     |
| <img width="30px" src="https://github.com/vinamra28.png">   | Vinamra Jain       | Red Hat | [vinamra28](https://github.com/vinamra28)      |

## Documentation

This is the documentation working group, related to
[`tektoncd/website`](https://github.com/tektoncd/website) and all
repository that need to expose documentation.

Connecting to the Meeting VC requires a Zoom account.

| Artifact                   | Link                       |
| -------------------------- | -------------------------- |
| Forum                      | [tekton-dev@](https://groups.google.com/forum/#!forum/tekton-dev) |
| Community Meeting VC       | [https://zoom.us/j/97950473778?pwd=MWk5TUFZYWxkRzhOcThFV3NMbXBXQT09](https://zoom.us/j/97950473778?pwd=MWk5TUFZYWxkRzhOcThFV3NMbXBXQT09) |
| Community Meeting Calendar | Tuesdays every week, 1:00pm-1:30pm EST <br>[Calendar](https://calendar.google.com/event?action=TEMPLATE&tmeid=NnNuNnViZjd2YmdvNnVmcWk2ZGFrZDJuY21fMjAyMjAyMjJUMTgwMDAwWiBnb29nbGUuY29tX2Qzb3Zjdm8xcDMyMTloOTg5NTczdjk4Zm5zQGc&tmsrc=google.com_d3ovcvo1p3219h989573v98fns%40group.calendar.google.com&scp=ALL) |
| Meeting Notes              | [Notes](https://docs.google.com/document/d/1nnJe4rWBFZORW9ScV9o-yk6BmvX419DDKKwIlORRhsY/edit) |
| Document Folder            | [Folder](https://drive.google.com/drive/folders/1dpGatrFh_Wykrs_tUkVK8hLNF1VaGHZd) |
| Slack Channel              | [#docs](https://tektoncd.slack.com/messages/docs) |


| &nbsp;                                                     | Facilitators     | Company | Profile                                     |
| --------------------------------------------------------   | ----------       | ------- | ---------------------------------------     |
| <img width="30px" src="https://github.com/afrittoli.png">  | Andrea Frittoli  | IBM     | [afrittoli](https://github.com/afritolli)   |
| <img width="30px" src="https://github.com/AlanGreene.png"> | Alan Greene      | IBM     | [AlanGreene](https://github.com/AlanGreene) |
| <img width="30px" src="https://github.com/geriom.png">     | Geri Ochoa       | Google  | [geriom](https://github.com/geriom)         |

## Productivity

This is the productivity working group, related to
[`tektoncd/plumbing`](https://github.com/tektoncd/plumbing) and the
productivity of tektoncd contributors in general. Topics for this working
group are _build captain_ updates, as well as development and maintenance
of the build, test and release infrastructure. One major aspect of this
working group is **dogfooding**, i.e. using Tekton itself to build, test
and release Tekton.

The meeting are created in the ET timezone. With daylight savings in the US
the time of the meetings remains the same, but it changes with respect to UTC
and other timezones.

Connecting to the Meeting VC requires a Zoom account.

| Artifact                   | Link                       |
| -------------------------- | -------------------------- |
| Forum                      | [tekton-dev@](https://groups.google.com/forum/#!forum/ |
| Meeting Notes              | [Notes](https://docs.google.com/document/d/1ZYqS2dDX8ary4dz_bImItbj8u4zwYtxII15kvylHYzs/edit) |
| Document Folder            | [Folder](https://drive.google.com/drive/folders/1QEj2TuIvxL6MvSSLwKucVOjpuVlydslP) |
| Slack Channel              | [#plumbing](https://tektoncd.slack.com/messages/plumbing) |

### Europe + North America

| Artifact                   | Link                       |
| -------------------------- | -------------------------- |
| Community Meeting VC       | [https://zoom.us/j/92490107166?pwd=OEIvbUk2aWlkaEl0dHhSeFUrYVlDQT09](https://zoom.us/j/92490107166?pwd=OEIvbUk2aWlkaEl0dHhSeFUrYVlDQT09) |
| Community Meeting Calendar | Thursdays 1:00pm-1:30pm ET <br>[Calendar](https://calendar.google.com/event?action=TEMPLATE&tmeid=bmwxdG9kcWtnbDJtNHYxNjByOHBwZ25wcXRfMjAyMTA0MDFUMTcwMDAwWiBhbmRyZWEuZnJpdHRvbGlAbQ&tmsrc=andrea.frittoli%40gmail.com&scp=ALL) |

| &nbsp;                                                        | Facilitators      | Company | Profile                                           |
| --------------------------------------------------------      | ----------        | ------- | ---------------------------------------           |
| <img width="30px" src="https://github.com/vdemeester.png">    | Vincent Demeester | Red Hat | [vdemeester](https://github.com/vdemeester)       |
| <img width="30px" src="https://github.com/afrittoli.png">     | Andrea Frittoli   | IBM     | [afrittoli](https://github.com/afrittoli)         |
| <img width="30px" src="https://github.com/bobcatfish.png">    | Christie Wilson   | Google  | [bobcatfish](https://github.com/bobcatfish)       |

### Europe + Asia

| Artifact                   | Link                       |
| -------------------------- | -------------------------- |
| Community Meeting VC       | [https://zoom.us/j/91999310007?pwd=OWEwVzROdE5nRisrWmNUa3g5aW4vZz09](https://zoom.us/j/91999310007?pwd=OWEwVzROdE5nRisrWmNUa3g5aW4vZz09) |
| Community Meeting Calendar | Thursdays 8:30pm-9:00pm ET <br>[Calendar](https://calendar.google.com/event?action=TEMPLATE&tmeid=NTBmYXBpMWR0OG5iMG5nb25mMm5vcW9ic2VfMjAyMTAzMjVUMTIzMDAwWiBhbmRyZWEuZnJpdHRvbGlAbQ&tmsrc=andrea.frittoli%40gmail.com&scp=ALL) |

| &nbsp;                                                        | Facilitators      | Company | Profile                                           |
| --------------------------------------------------------      | ----------        | ------- | ---------------------------------------           |
| <img width="30px" src="https://github.com/savitaashture.png"> | Savita Asthure    | Red Hat | [savitaashture](https://github.com/savitaashture) |
| <img width="30px" src="https://github.com/nikhil-thomas.png"> | Nikhil Thomas     | Red Hat | [nikhil-thomas](https://github.com/nikhil-thomas) |
| <img width="30px" src="https://github.com/vdemeester.png">    | Vincent Demeester | Red Hat | [vdemeester](https://github.com/vdemeester)       |
| <img width="30px" src="https://github.com/afrittoli.png">     | Andrea Frittoli   | IBM     | [afrittoli](https://github.com/afrittoli)         |

## API

This working group is all about proposing and discussing changes to the Tekton
Pipelines API. Changes to the Pipelines API have ramifications for all other
Tekton projects.

| Artifact                   | Link                       |
| -------------------------- | -------------------------- |
| Forum                      | [tekton-dev@](https://groups.google.com/forum/#!forum/tekton-dev) |
| Meeting Notes              | [Notes](https://docs.google.com/document/d/17PodAxG8hV351fBhSu7Y_OIPhGTVgj6OJ2lPphYYRpU/edit)
| Slack Channel              | [#pipeline-dev](https://tektoncd.slack.com/messages/pipeline-dev) |

### Europe + North America

| Artifact                   | Link                       |
| -------------------------- | -------------------------- |
| Community Meeting VC       | [https://meet.google.com/tse-axnh-mdv](https://meet.google.com/tse-axnh-mdv) |
| Community Meeting Calendar | Mondays every week, 09:00a-10:00a PST <br>[Calendar](https://calendar.google.com/event?action=TEMPLATE&tmeid=YnBscG9lcGk3b3ZrN3VxZWpjaXRsMm1uNmJfMjAyMDA0MTNUMTYwMDAwWiBnb29nbGUuY29tX2Qzb3Zjdm8xcDMyMTloOTg5NTczdjk4Zm5zQGc&tmsrc=google.com_d3ovcvo1p3219h989573v98fns%40group.calendar.google.com&scp=ALL)

| &nbsp;                                                     | Facilitators      | Company | Profile                                     |
| --------------------------------------------------------   | ----------        | ------- | ---------------------------------------     |
| <img width="30px" src="https://github.com/bobcatfish.png"> | Christie Wilson   | Google  | [bobcatfish](https://github.com/bobcatfish) |
| <img width="30px" src="https://github.com/vdemeester.png"> | Vincent Demeester | Red Hat | [vdemeester](https://github.com/vdemeester) |
| <img width="30px" src="https://github.com/afrittoli.png">  | Andrea Frittoli   | IBM     | [afrittoli](https://github.com/afrittoli)   |
| <img width="30px" src="https://github.com/skaegi.png">     | Simon Kaegi       | IBM     | [skaegi](https://github.com/skaegi)         |
| <img width="30px" src="https://github.com/dibyom.png">     | Dibyo Mukherjee   | Google  | [dibyom](https://github.com/dibyom)         |
| <img width="30px" src="https://github.com/pritidesai.png"> | Priti Desai       | IBM     | [pritidesai](https://github.com/pritidesai) |

### Australia + North America

| Artifact                   | Link                       |
| -------------------------- | -------------------------- |
| Community Meeting VC       | [https://meet.google.com/nyw-cwme-iia](https://meet.google.com/nyw-cwme-iia) |
| Community Meeting Calendar | Mondays every other week, 3:00pm-3:30pm PST <br>[Calendar](https://calendar.google.com/event?action=TEMPLATE&tmeid=Mm40OXM2NzRuaXY1Z3J2dTRnNDBiZzk0N3FfMjAyMTA0MjZUMjIwMDAwWiBjaHJpc3RpZXdpbHNvbkBnb29nbGUuY29t&tmsrc=christiewilson%40google.com&scp=ALL)|

| &nbsp;                                                      | Facilitators      | Company      | Profile                                       |
| --------------------------------------------------------    | ----------        | -------      | ---------------------------------------       |
| <img width="30px" src="https://github.com/bobcatfish.png">  | Christie Wilson   | Google       | [bobcatfish](https://github.com/bobcatfish)   |
| <img width="30px" src="https://github.com/skaegi.png">      | Simon Kaegi       | IBM          | [skaegi](https://github.com/skaegi)           |
| <img width="30px" src="https://github.com/jerop.png">       | Jerop Kipruto     | Google       | [jerop](https://github.com/jerop)             |

## Dashboard

This is the [`tektoncd/dashboard`](https://github.com/tektoncd/dashboard) working group.

| Artifact                   | Link                       |
| -------------------------- | -------------------------- |
| Forum                      | [tekton-dev@](https://groups.google.com/forum/#!forum/tekton-dev) |
| Community Meeting VC       | [https://meet.google.com/zxa-zefw-zum](https://meet.google.com/zxa-zefw-zum) |
| Community Meeting Calendar | Mondays every week, 4:00pm-4:30pm CET <br>[Calendar](https://calendar.google.com/event?action=TEMPLATE&tmeid=b3NxODE2YjlrY3NzMnYwMmpmamY5NnVobHFfMjAyMDAzMTZUMTUwMDAwWiBnb29nbGUuY29tX2Qzb3Zjdm8xcDMyMTloOTg5NTczdjk4Zm5zQGc&tmsrc=google.com_d3ovcvo1p3219h989573v98fns%40group.calendar.google.com&scp=ALL) |
| Meeting Notes              | [Notes](https://docs.google.com/document/d/1bG4mbjycmFtIBezA6AJoQvaB4-v3874dhX7n-DhGAx0/edit) |
| Document Folder            | [Folder](https://drive.google.com/drive/folders/1SCS7q9Ns9m8p7MG_4URiFKirz1SgID_B) |
| Slack Channel              | [#dashboard](https://tektoncd.slack.com/messages/dashboard) |

| &nbsp;                                                        | Facilitators    | Company | Profile                                            |
| -----------------------------------------------------------   | ----------      | ------- | ------------------------------------------------   |
| <img width="30px" src="https://github.com/a-roberts.png">     | Adam Roberts    | IBM     | [a-roberts](https://github.com/a-roberts)          |
| <img width="30px" src="https://github.com/mnuttall.png">      | Mark Nuttall    | IBM     | [mnuttall](https://github.com/mnuttall)            |
| <img width="30px" src="https://github.com/skaegi.png">        | Simon Kaegi     | IBM     | [skaegi](https://github.com/skaegi)                |
| <img width="30px" src="https://github.com/dibbles.png">       | Duane Appleby   | IBM     | [dibbles](https://github.com/dibbles)              |
| <img width="30px" src="https://github.com/steveodonovan.png"> | Steve O'Donovan | IBM     | [steveodonovan](https://github.com/steveodonovan)  |
| <img width="30px" src="https://github.com/AlanGreene.png">    | Alan Greene     | IBM     | [AlanGreene](https://github.com/AlanGreene)        |

## Catalog and hub

This is the working group for [`tektoncd/catalog`](https://github.com/tektoncd/catalog) and [`tektoncd/hub`](https://github.com/tektoncd/hub).

| Artifact                   | Link                       |
| -------------------------- | -------------------------- |
| Forum                      | [tekton-dev@](https://groups.google.com/forum/#!forum/tekton-dev) |
| Community Meeting VC       | [https://meet.google.com/nkt-mziz-ifz](https://meet.google.com/nkt-mziz-ifz) |
| Community Meeting Calendar | Thursdays every week, 10:30am-11am PST <br>[Calendar](https://calendar.google.com/event?action=TEMPLATE&tmeid=NzFzcWhkOGk2MWNzMTI0cGg3MDA4YmUzMHZfMjAyMDA1MTRUMTczMDAwWiBjaHJpc3RpZXdpbHNvbkBnb29nbGUuY29t&tmsrc=christiewilson%40google.com&scp=ALL) |
| Meeting Notes              | [Notes](https://docs.google.com/document/d/12180Mqmhoj5JK17zE07DG3OdqYHcUAWVBGydavoxhec/edit) |
| Slack Channels             | [#catalog](https://tektoncd.slack.com/messages/catalog) and [#hub](https://tektoncd.slack.com/messages/hub) |

| &nbsp;                                                        | Facilitators      | Company | Profile                                            |
| -----------------------------------------------------------   | ----------        | ------- | ------------------------------------------------   |
| <img width="30px" src="https://github.com/vdemeester.png">    | Vincent Demeester | Red Hat | [vdemeester](https://github.com/vdemeester)        |
| <img width="30px" src="https://github.com/chmouel.png">       | Chmouel Boudjnah  | Red Hat | [chmouel](https://github.com/chmouel)              |
| <img width="30px" src="https://github.com/afrittoli.png">     | Andrea Frittoli   | IBM     | [afrittoli](https://github.com/afrittoli)          |
| <img width="30px" src="https://github.com/piyush-garg.png">   | Piyush Garg       | Red Hat | [piyush-garg](https://github.com/piyush-garg)      |
| <img width="30px" src="https://github.com/vinamra28.png">   | Vinamra Jain       | Red Hat | [vinamra28](https://github.com/vinamra28)      |

## Operator and Deployment

This is the working group for [`tektoncd/operator`](https://github.com/tektoncd/operator)

| Artifact                   | Link                       |
| -------------------------- | -------------------------- |
| Forum                      | [tekton-dev@](https://groups.google.com/forum/#!forum/tekton-dev) |
| Community Meeting VC       | [https://meet.google.com/zzp-gzmd-dys](https://meet.google.com/zzp-gzmd-dys) |
| Community Meeting Calendar | Thursdays every week, 4am -4:30am PST <br>[Calendar](https://calendar.google.com/event?action=TEMPLATE&tmeid=NzFzcWhkOGk2MWNzMTI0cGg3MDA4YmUzMHZfMjAyMDA1MTRUMTczMDAwWiBjaHJpc3RpZXdpbHNvbkBnb29nbGUuY29t&tmsrc=christiewilson%40google.com&scp=ALL) |
| Meeting Notes              | [Notes](https://docs.google.com/document/d/1mMbwPCTzDCRgr0FNtv8TJaKDfiOfD9pgz1zFmncZReg/edit) |
| Slack Channels             | [#operator](https://tektoncd.slack.com/messages/operator) |

| &nbsp;                                                        | Facilitators  | Company | Profile                                           |
| -----------------------------------------------------------   | ----------    | ------- | ------------------------------------------------  |
| <img width="30px" src="https://github.com/nikhil-thomas.png"> | Nikhil Thomas | Red Hat | [nikhil-thomas](https://github.com/nikhil-thomas) |
| <img width="30px" src="https://github.com/houshengbo.png">    | Vincent Hou   | IBM     | [houshengbo](https://github.com/houshengbo)       |
| <img width="30px" src="https://github.com/khrm.png">          | Khurram Baig  | Red Hat | [khrm](https://github.com/khrm)                   |
| <img width="30px" src="https://github.com/pgarg.png">         | Piyush Garg   | Red Hat | [piyush-garg](https://github.com/piyush-garg)     |
| <img width="30px" src="https://github.com/sthaha.png">        | Sunil Thaha   | Red Hat | [sthaha](https://github.com/sthaha)               |

## Chains

This is the working group for [`tektoncd/chains`](https://github.com/tektoncd/chains)

| Artifact                   | Link                       |
| -------------------------- | -------------------------- |
| Forum                      | [tekton-dev@](https://groups.google.com/forum/#!forum/tekton-dev) |
| Community Meeting VC       | [https://meet.google.com/ktu-xuqo-uyc](https://meet.google.com/ktu-xuqo-uyc) |
| Community Meeting Calendar | Thursdays every other week, 9am -9:30am PST <br>[Calendar](https://calendar.google.com/event?action=TEMPLATE&tmeid=Nzc3N2VjZjk3amZnZzc5MDQwODYxNzRrZHVfMjAyMTA4MTlUMTYwMDAwWiBnb29nbGUuY29tX2Qzb3Zjdm8xcDMyMTloOTg5NTczdjk4Zm5zQGc&tmsrc=google.com_d3ovcvo1p3219h989573v98fns%40group.calendar.google.com&scp=ALL) |
| Meeting Notes              | [Notes](https://docs.google.com/document/d/1UVPSCDyNO-TzEFSv8jrqrEOF_FmV8NFuXncFm1gwmeY/edit) |
| Slack Channels             | [#chains](https://tektoncd.slack.com/messages/chains) |

| &nbsp;                                                         | Facilitators    | Company    | Profile                                           |
| -----------------------------------------------------------    | ----------      | ---------- | ------------------------------------------------  |
| <img width="30px" src="https://github.com/priyawadhwa.png">    | Priya Wadhwa    | Chainguard | [priyawadhwa](https://github.com/priyawadhwa)     |
| <img width="30px" src="https://github.com/pritidesai.png">     | Priti Desai     | IBM        | [pritidesai](https://github.com/pritidesai) |
| <img width="30px" src="https://github.com/bobcatfish.png">     | Christie Wilson | Google     | [bobcatfish](https://github.com/bobcatfish) |
| <img width="30px" src="https://github.com/wlynch.png">         | Billy Lynch     | Google     | [wlynch](https://github.com/wlynch) |

## Workflows

Topics for this WG include the experimental [Tekton Workflows](https://github.com/tektoncd/experimental/tree/main/workflows), [Pipelines as Code](https://github.com/openshift-pipelines/pipelines-as-code), [Remote Resolution](https://github.com/tektoncd/community/blob/main/teps/0060-remote-resource-resolution.md) etc.

| Artifact                   | Link                       |
| -------------------------- | -------------------------- |
| Forum                      | [tekton-dev@](https://groups.google.com/forum/#!forum/tekton-dev) |
| Community Meeting VC       | [meet.google.com/jwa-pxmv-vpi](https://meet.google.com/jwa-pxmv-vpi) |
| Community Meeting Calendar | Tuesdays every week, 10am -10:30am ET <br>[Calendar](https://calendar.google.com/event?action=TEMPLATE&tmeid=NDl0bzN1OWl2dWxlMXBpNGFnaDhjM2N2NjRfMjAyMTA5MDdUMTQwMDAwWiBnb29nbGUuY29tX2Qzb3Zjdm8xcDMyMTloOTg5NTczdjk4Zm5zQGc&tmsrc=google.com_d3ovcvo1p3219h989573v98fns%40group.calendar.google.com&scp=ALL) |
| Meeting Notes              | [Notes](https://docs.google.com/document/d/1di4ikeVb8Mksgbq4CzW4m4xUQPZ2dQMLvK1VIJw7OQg/edit) |
| Slack Channels             | [#workflows](https://tektoncd.slack.com/messages/workflows) |


| &nbsp;                                                           | Facilitators     | Company     | Profile                                                 |
| --------------------------------------------------------         | ----------       | -------     | ---------------------------------------                 |
| <img width="30px" src="https://github.com/dibyom.png">           | Dibyo Mukherjee  | Google      | [dibyom](https://github.com/dibyom)                     |
| <img width="30px" src="https://github.com/sbwsg.png">            | Scott Seaward    | Google      | [sbwsg](https://github.com/sbwsg)                       |
| <img width="30px" src="https://github.com/khrm.png">             | Khurram Baig     | Red Hat     | [khrm](https://github.com/khrm)                         |
| <img width="30px" src="https://github.com/chmouel.png">          | Chmouel Boudjnah | Red Hat     | [chmouel](https://github.com/chmouel)                   |

## Pipeline

This is the working group for [`tektoncd/pipeline`](https://github.com/tektoncd/pipeline).
Connecting to the Meeting VC requires a Zoom account.

| Artifact                   | Link                       |
| -------------------------- | -------------------------- |
| Forum                      | [tekton-dev@](https://groups.google.com/forum/#!forum/tekton-dev) |
| Meeting Notes              | [Notes](https://docs.google.com/document/d/1AfJfdyd1JN2P4haBdYOxEn6SMENMgvQF9ps7iF2QSG0/edit)
| Slack Channel              | [#pipeline-dev](https://tektoncd.slack.com/messages/pipeline-dev) |
| Community Meeting VC       | [https://zoom.us/j/98272582734?pwd=OTBVMWJIbVJZcUU3WnlodTEvVS9PUT09](https://zoom.us/j/98272582734?pwd=OTBVMWJIbVJZcUU3WnlodTEvVS9PUT09) |
| Community Meeting Calendar | Tuesday every other week, 09:30a-10:00a PST <br>[Calendar](https://calendar.google.com/event?action=TEMPLATE&tmeid=NG5jdWV0ZTFxaGo0MHNpYzVnODlrYXZucGhfMjAyMTExMDJUMTYzMDAwWiBnb29nbGUuY29tX2Qzb3Zjdm8xcDMyMTloOTg5NTczdjk4Zm5zQGc&tmsrc=google.com_d3ovcvo1p3219h989573v98fns%40group.calendar.google.com&scp=ALL) |


| &nbsp;                                                     | Facilitators      | Company | Profile                                     |
| --------------------------------------------------------   | ----------        | ------- | ---------------------------------------     |
| <img width="30px" src="https://github.com/afrittoli.png">  | Andrea Frittoli   | IBM     | [afrittoli](https://github.com/afrittoli)   |
| <img width="30px" src="https://github.com/bobcatfish.png"> | Christie Wilson   | Google  | [bobcatfish](https://github.com/bobcatfish) |
| <img width="30px" src="https://github.com/dibyom.png">     | Dibyo Mukherjee   | Google  | [dibyom](https://github.com/dibyom)         |
| <img width="30px" src="https://github.com/jerop.png">      | Jerop Kipruto     | Google  | [jerop](https://github.com/jerop)           |
| <img width="30px" src="https://github.com/pritidesai.png"> | Priti Desai       | IBM     | [pritidesai](https://github.com/pritidesai) |
| <img width="30px" src="https://github.com/vdemeester.png"> | Vincent Demeester | Red Hat | [vdemeester](https://github.com/vdemeester) |

## Governing Board / Community

This is the sync meeting for [the Tekton governing board](https://github.com/tektoncd/community/blob/main/governance.md#tekton-governance-committee)
and a place to discuss community operations and process.

| Artifact                   | Link                       |
| -------------------------- | -------------------------- |
| Forum                      | [tekton-dev@](https://groups.google.com/forum/#!forum/tekton-dev) |
| Meeting Notes              | [Notes](https://docs.google.com/document/d/1rb-JgpZGVRvY6tj5yjh3jeaxUxqeyk8Sudd7gMFtqqA/edit)
| Slack Channel              | [#governance](https://tektoncd.slack.com/messages/governance) |
| Community Meeting VC       | [meet.google.com/nas-vyqv-ftg](https://meet.google.com/nas-vyqv-ftg) |
| Community Meeting Calendar | Tuesday every other week, 09:00a-09:30a PST <br>[Calendar](https://calendar.google.com/event?action=TEMPLATE&tmeid=NjFvcHNib2E2cjNwcGc2dGhnMmY2OGU4YTFfMjAyMjAxMThUMTcwMDAwWiBnb29nbGUuY29tX2Qzb3Zjdm8xcDMyMTloOTg5NTczdjk4Zm5zQGc&tmsrc=google.com_d3ovcvo1p3219h989573v98fns%40group.calendar.google.com&scp=ALL) |


| &nbsp;                                                     | Facilitators      | Company   | Profile                                     |
| --------------------------------------------------------   | ----------        | -------   | ---------------------------------------     |
| <img width="30px" src="https://github.com/abayer.png">     | Andrew Bayer      | CloudBees | [abayer](https://github.com/abayer) |
| <img width="30px" src="https://github.com/afrittoli.png">  | Andrea Frittoli   | IBM       | [afrittoli](https://github.com/afrittoli)   |
| <img width="30px" src="https://github.com/bobcatfish.png"> | Christie Wilson   | Google    | [bobcatfish](https://github.com/bobcatfish) |
| <img width="30px" src="https://github.com/dibyom.png">     | Dibyo Mukherjee   | Google    | [dibyom](https://github.com/dibyom)         |
| <img width="30px" src="https://github.com/vdemeester.png"> | Vincent Demeester | Red Hat   | [vdemeester](https://github.com/vdemeester) |

## Software Supply Chain Security (s3c)

The goal of this working group is to discuss supply chain security initiatives across Tekton (exact scope 
TBD [community#629](https://github.com/tektoncd/community/issues/629)).

| Artifact                   | Link                       |
| -------------------------- | -------------------------- |
| Forum                      | [tekton-dev@](https://groups.google.com/forum/#!forum/tekton-dev) |
| Meeting Notes              | [Discussion board](https://github.com/orgs/tektoncd/projects/14/views/1), [HackMD Notes](https://hackmd.io/gFcAZMFMRwuTaZ1i7Y3fSg)
| Slack Channel              | [#security](https://tektoncd.slack.com/messages/security) |
| Community Meeting VC       | [meet.google.com/utk-kdff-hci](https://meet.google.com/utk-kdff-hci) |
| Community Meeting Calendar | Tuesday every other week, 09:00a-09:30a PST <br>[Calendar](https://calendar.google.com/event?action=TEMPLATE&tmeid=NDFuMjg2OTloYTJrYm1jNGM1dWZiZ3JzdGZfMjAyMjAyMjJUMTcwMDAwWiBjaHJpc3RpZXdpbHNvbkBnb29nbGUuY29t&tmsrc=christiewilson%40google.com&scp=ALL) |


| &nbsp;                                                     | Facilitators      | Company   | Profile                                     |
| --------------------------------------------------------   | ----------        | -------   | ---------------------------------------     |
| <img width="30px" src="https://github.com/pritidesai.png"> | Priti Desai       | IBM       | [pritidesai](https://github.com/pritidesai) |
| <img width="30px" src="https://github.com/imjasonh.png">   | Jason Hall        | Red Hat   | [imjasonh](https://github.com/imjasonh)     |
| <img width="30px" src="https://github.com/bobcatfish.png"> | Christie Wilson   | Google    | [bobcatfish](https://github.com/bobcatfish) |
| <img width="30px" src="https://github.com/afrittoli.png">  | Andrea Frittoli   | IBM       | [afrittoli](https://github.com/afrittoli)   |
| <img width="30px" src="https://github.com/xchapter7x.png"> | John Calabrese    | Google    | [xchapter7x](https://github.com/xchapter7x) |
