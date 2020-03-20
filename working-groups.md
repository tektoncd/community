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
- [Beta release](#beta-release)
- [Dashboard](#dashboard)

## General

This is the general working group, where we discuss each project's
update and cross-project subjects. This is also the main working group
to discuss the `tektoncd/pipeline` project.

We altenate between two meeting times, a time that is friendly for Europe + North America
(PST+EST+CEST) and a time that is friendly for Asia + Europe (CEST+IST+CST).


| Artifact                   | Link                                                                                                                                                                                                                                                                                                 |
| -------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------                                                                                                                                        |
| Forum                      | [tekton-dev@](https://groups.google.com/forum/#!forum/tekton-dev)                                                                                                                                                                                                                                    |
| Slack Channel              | [#pipeline](https://tektoncd.slack.com/messages/pipeline)                                                                                                                                                                                                                                            |
| Meeting Notes              | [Notes](https://docs.google.com/document/d/1rPR7m1Oj0ip3bpd_bcS1sjZyPgGi_g9asF5YrExeESc)                                                                                                                                                                                                             |

### Europe + North America


| Artifact                   | Link                                                                                                                                                                                                                                                                                                 |
| -------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------                                                                                                                                        |
| Community Meeting VC       | [https://meet.google.com/gnx-mwhf-wqt](https://meet.google.com/gnx-mwhf-wqt)                                                                                                                                                                                                                                         |
| Community Meeting Calendar | Wednesdays 9:00am-10:00am PST <br>[Calendar](https://calendar.google.com/event?action=TEMPLATE&tmeid=bjc0aWJqMzVtYm04ZWt2NHJlajJmajdvNGtfMjAxOTA1MjlUMTYwMDAwWiBnb29nbGUuY29tX2Qzb3Zjdm8xcDMyMTloOTg5NTczdjk4Zm5zQGc&tmsrc=google.com_d3ovcvo1p3219h989573v98fns%40group.calendar.google.com&scp=ALL) |
| Meeting Notes              | [Notes](https://docs.google.com/document/d/1rPR7m1Oj0ip3bpd_bcS1sjZyPgGi_g9asF5YrExeESc)                                                                                                                                                                                                             |

| &nbsp;                                                     | Facilitators      | Company | Profile                                     |
| --------------------------------------------------------   | ----------        | ------- | ---------------------------------------     |
| <img width="30px" src="https://github.com/bobcatfish.png"> | Christie Wilson   | Google  | [bobcatfish](https://github.com/bobcatfish) |
| <img width="30px" src="https://github.com/vdemeester.png"> | Vincent Demeester | Red Hat | [vdemeester](https://github.com/vdemeester) |
| <img width="30px" src="https://github.com/skaegi.png">     | Simon Kaegi       | IBM     | [skaegi](https://github.com/skaegi)         |
| <img width="30px" src="https://github.com/dlorenc.png">    | Dan Lorenc        | Google  | [dlorenc](https://github.com/dlorenc)       |

### Europe + Asia

| Artifact                   | Link                                                                                                                                                                                                                                                                                                 |
| -------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------                                                                                                                                        |
| Community Meeting VC       | [meet.google.com/xgi-shbo-mym](https://meet.google.com/xgi-shbo-mym)                                                                                                                                                                                                                                         |
| Community Meeting Calendar | Wednesdays 8:30pm-9:30pm CST <br>[Calendar](https://calendar.google.com/event?action=TEMPLATE&tmeid=M3Rsa2lsdnA5ZGc2aHJ1bGlqdGUzOXFnYjNfMjAyMDAxMjJUMTIzMDAwWiBnb29nbGUuY29tX2Qzb3Zjdm8xcDMyMTloOTg5NTczdjk4Zm5zQGc&tmsrc=google.com_d3ovcvo1p3219h989573v98fns%40group.calendar.google.com&scp=ALL) |
| Meeting Notes              | [Notes](https://docs.google.com/document/d/1rPR7m1Oj0ip3bpd_bcS1sjZyPgGi_g9asF5YrExeESc)                                                                                                                                                                                                             |


| &nbsp;                                                     | Facilitators      | Company | Profile                                     |
| --------------------------------------------------------   | ----------        | ------- | ---------------------------------------     |
| <img width="30px" src="https://github.com/afrittoli.png">  | Andrea Frittoli   | IBM     | [afrittoli](https://github.com/afrittoli) |
| <img width="30px" src="https://github.com/vdemeester.png"> | Vincent Demeester | Red Hat | [vdemeester](https://github.com/vdemeester) |

## Triggers

This is the [`tektoncd/triggers`](https://github.com/tektoncd/triggers) working group.

| Artifact                   | Link                                                                                                                                                                                                                                      |
| -------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------                                                                             |
| Forum                      | [tekton-dev@](https://groups.google.com/forum/#!forum/tekton-dev)                                                                                                                                                                         |
| Community Meeting VC       | [https://meet.google.com/oqm-imjh-uzu](https://meet.google.com/oqm-imjh-uzu)                                                                                                                                                              |
| Community Meeting Calendar | Tuesdays every week, 12:00p-12:30p PST <br>[Calendar](https://calendar.google.com/event?action=TEMPLATE&tmeid=ZmNmbWtnNGxzcG1uaGUwNm9rMHB1MzR2ZnJfMjAyMDAxMjhUMTcwMDAwWiBnb29nbGUuY29tX2Qzb3Zjdm8xcDMyMTloOTg5NTczdjk4Zm5zQGc&tmsrc=google.com_d3ovcvo1p3219h989573v98fns%40group.calendar.google.com&scp=ALL) |
| Meeting Notes              | [Notes](https://docs.google.com/document/d/1T87yK4BIu291gGK1L2ZzDpesGCnXX3tGuWXjdr5Soxw/edit)                                                                                                                                             |
| Document Folder            | [Folder](https://drive.google.com/drive/folders/1-UOR-sodtMeYqtUEzVW12nkfJCr7EQRO)                                                                                                                                                        |
| Slack Channel              | [#triggers](https://tektoncd.slack.com/messages/triggers)                                                                                                                                                                                 |


| &nbsp;                                                     | Facilitators    | Company | Profile                                     |
| --------------------------------------------------------   | ----------      | ------- | ---------------------------------------     |
| <img width="30px" src="https://github.com/wlynch.png">     | Billy Lynch     | Google  | [wlynch](https://github.com/wlynch)         |
| <img width="30px" src="https://github.com/dibyom.png">     | Dibyo Mukherjee | Google  | [dibyom](https://github.com/dibyom)         |
| <img width="30px" src="https://github.com/vtereso.png">    | Vincent Tereso  | IBM     | [vtereso](https://github.com/vtereso)       |
| <img width="30px" src="https://github.com/ncskier.png">    | Brandon Walker  | IBM     | [ncskier](https://github.com/ncskier)       |
| <img width="30px" src="https://github.com/bobcatfish.png"> | Christie Wilson | Google  | [bobcatfish](https://github.com/bobcatfish) |

## CLI

This is the [`tektoncd/cli`](https://github.com/tektoncd/cli) working group.

| Artifact                   | Link                                                                                                                                                                                                                        |
| -------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------                                                               |
| Forum                      | [tekton-dev@](https://groups.google.com/forum/#!forum/tekton-dev)                                                                                                                                                           |
| Community Meeting VC       | [https://meet.google.com/mwj-mfpy-ybk](https://meet.google.com/mwj-mfpy-ybk)                                                                                                                                                |
| Community Meeting Calendar | Tuesdays 08:00a-08:30a EST <br>[Calendar](https://calendar.google.com/event?action=TEMPLATE&tmeid=ZmV1ZmI2dnJjYm9wYWFkaXNxdWJuOWo1bWRfMjAyMDAxMjhUMTMwMDAwWiBnb29nbGUuY29tX2Qzb3Zjdm8xcDMyMTloOTg5NTczdjk4Zm5zQGc&tmsrc=google.com_d3ovcvo1p3219h989573v98fns%40group.calendar.google.com&scp=ALL) |
| Meeting Notes              | [Notes](https://docs.google.com/document/d/1J1LkrmLtMdtdJqFcsyOKsJJc4lEm7YL-97D51PzpHrQ/edit)                                                                                                                               |
| Document Folder            | [Folder](https://drive.google.com/drive/folders/1FnMx4h8WkeBEo3vYl3w2IAOa-otf_a2j)                                                                                                                                          |
| Slack Channel              | [#cli](https://tektoncd.slack.com/messages/cli)                                                                                                                                                                             |


| &nbsp;                                                        | Facilitators      | Company | Profile                                           |
| --------------------------------------------------------      | ----------        | ------- | ---------------------------------------           |
| <img width="30px" src="https://github.com/vdemeester.png">    | Vincent Demeester | Red Hat | [vdemeester](https://github.com/vdemeester)       |
| <img width="30px" src="https://github.com/chmouel.png">       | Chmouel Boudjnah  | Red Hat | [chmouel](https://github.com/chmouel)             |
| <img width="30px" src="https://github.com/danielhelfand.png"> | Daniel Helfand    | VMware  | [danielhelfand](https://github.com/danielhelfand) |

## Documentation

This is the documentation working group, related to
[`tektoncd/website`](https://github.com/tektoncd/website) and all
repository that need to expose documentation.

| Artifact                   | Link                                                                                                                                                                                                                                         |
| -------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------                                                                                |
| Forum                      | [tekton-dev@](https://groups.google.com/forum/#!forum/tekton-dev)                                                                                                                                                                            |
| Community Meeting VC       | [https://meet.google.com/hyc-nunv-hts](https://meet.google.com/hyc-nunv-hts)                                                                                                                                                                 |
| Community Meeting Calendar | Wednesdays every week, 01:00p-01:30p EST <br>[Calendar](https://calendar.google.com/event?action=TEMPLATE&tmeid=MW9oZzNpbmkxbHU5ZGtlN2hnMzVsYjNpcTJfMjAyMDAxMjlUMTgwMDAwWiBnb29nbGUuY29tX2Qzb3Zjdm8xcDMyMTloOTg5NTczdjk4Zm5zQGc&tmsrc=google.com_d3ovcvo1p3219h989573v98fns%40group.calendar.google.com&scp=ALL) |
| Meeting Notes              | [Notes](https://www.google.com/url?q=https://docs.google.com/document/d/1nnJe4rWBFZORW9ScV9o-yk6BmvX419DDKKwIlORRhsY/edit%23&sa=D&ust=1575716141397000&usg=AOvVaw0IMqtfI1KeX8a6zq2ODl9n)                                                     |
| Document Folder            | [Folder](https://drive.google.com/drive/folders/1dpGatrFh_Wykrs_tUkVK8hLNF1VaGHZd)                                                                                                                                                           |
| Slack Channel              | [#docs](https://tektoncd.slack.com/messages/docs)                                                                                                                                                                                            |


| &nbsp;                                                     | Facilitators      | Company | Profile                                     |
| --------------------------------------------------------   | ----------        | ------- | ---------------------------------------     |
| <img width="30px" src="https://github.com/kimsterv.png">   | Kim Lewandowski   | Google  | [kimsterv](https://github.com/kimsterv)     |
| <img width="30px" src="https://github.com/spomorski.png">  | Serge Pomorski    | Google  | [spomorski](https://github.com/spomorski)   |
| <img width="30px" src="https://github.com/vdemeester.png"> | Vincent Demeester | Red Hat | [vdemeester](https://github.com/vdemeester) |

## Productivity

This is the productivity working group, related to
[`tektoncd/plumbing`](https://github.com/tektoncd/plumbing) and the
productivity of tektoncd contributors in general. One *current* major
aspect of this working group for now is **dogfooding**.

| Artifact                   | Link                                                                                                                                                                                                                        |
| -------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------                                                               |
| Forum                      | [tekton-dev@](https://groups.google.com/forum/#!forum/tekton-dev)                                                                                                                                                           |
| Community Meeting VC       | [https://meet.google.com/yja-jajy-ter](https://meet.google.com/yja-jajy-ter)                                                                                                                                                |
| Community Meeting Calendar | Thursdays 1:00pm-1:30pm EST <br>[Calendar](https://calendar.google.com/event?action=TEMPLATE&tmeid=dm90cnFuZmRucmgwdW90bTF1YmdmMHNxYWdfMjAyMDAxMzBUMTgwMDAwWiBnb29nbGUuY29tX2Qzb3Zjdm8xcDMyMTloOTg5NTczdjk4Zm5zQGc&tmsrc=google.com_d3ovcvo1p3219h989573v98fns%40group.calendar.google.com&scp=ALL) |
| Meeting Notes              | [Notes](https://docs.google.com/document/d/1ZYqS2dDX8ary4dz_bImItbj8u4zwYtxII15kvylHYzs/edit)                                                                                                                               |
| Document Folder            | [Folder](https://drive.google.com/drive/folders/1QEj2TuIvxL6MvSSLwKucVOjpuVlydslP)                                                                                                                                          |
| Slack Channel              | [#plumbing](https://tektoncd.slack.com/messages/plumbing)                                                                                                                                                                   |



| &nbsp;                                                     | Facilitators      | Company | Profile                                     |
| --------------------------------------------------------   | ----------        | ------- | ---------------------------------------     |
| <img width="30px" src="https://github.com/vdemeester.png"> | Vincent Demeester | Red Hat | [vdemeester](https://github.com/vdemeester) |
| <img width="30px" src="https://github.com/afrittoli.png">  | Andrea Frittoli   | IBM     | [afrittoli](https://github.com/afrittoli)   |
| <img width="30px" src="https://github.com/bobcatfish.png"> | Christie Wilson   | Google  | [bobcatfish](https://github.com/bobcatfish) |

## Beta release

This is the beta release working group, related to the work towards
the beta API releases of
[`tektoncd/pipeline`](https://github.com/tektoncd/pipeline) APIs. This
is a temporary working group.

| Artifact                   | Link                                                                                                                                                                                                                                                                                                             |
| -------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------                                                                                                                                                    |
| Forum                      | [tekton-dev@](https://groups.google.com/forum/#!forum/tekton-dev)                                                                                                                                                                                                                                                |
| Community Meeting VC       | [https://meet.google.com/tse-axnh-mdv](https://meet.google.com/tse-axnh-mdv)                                                                                                                                                                                                                                     |
| Community Meeting Calendar | Mondays every 2 weeks, 09:00a-10:00a EST <br>[Calendar](https://calendar.google.com/event?action=TEMPLATE&tmeid=NXRiamQwbWh1ajk0OTEyOTY0YjVzcXBnbGJfMjAxOTA5MjNUMTYwMDAwWiBnb29nbGUuY29tX2Qzb3Zjdm8xcDMyMTloOTg5NTczdjk4Zm5zQGc&tmsrc=google.com_d3ovcvo1p3219h989573v98fns%40group.calendar.google.com&scp=ALL) |
| Meeting Notes              | [Notes](https://docs.google.com/document/d/1JmRd0vbh2Q6Emu2DOk-LwLHfxd2V0zrN4WNawGzoNXw)                                                                                                                                                                                                                         |
| Slack Channel              | [#pipeline-dev](https://tektoncd.slack.com/messages/pipeline-dev)                                                                                                                                                                                                                                                |



| &nbsp;                                                     | Facilitators    | Company | Profile                                     |
| --------------------------------------------------------   | ----------      | ------- | ---------------------------------------     |
| <img width="30px" src="https://github.com/bobcatfish.png"> | Christie Wilson | Google  | [bobcatfish](https://github.com/bobcatfish) |



## Dashboard

This is the [`tektoncd/dashboard`](https://github.com/tektoncd/dashboard) working group.

| Artifact                   | Link                                                                                                                                                                                                                                      |
| -------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------                                                                             |
| Forum                      | [tekton-dev@](https://groups.google.com/forum/#!forum/tekton-dev)                                                                                                                                                                         |
| Community Meeting VC       | [https://meet.google.com/zxa-zefw-zum](https://meet.google.com/zxa-zefw-zum)                                                                                                                                                              |
| Community Meeting Calendar | Mondays every week, 4:00pm-4:30pm CET <br>[Calendar](https://calendar.google.com/event?action=TEMPLATE&tmeid=b3NxODE2YjlrY3NzMnYwMmpmamY5NnVobHFfMjAyMDAzMTZUMTUwMDAwWiBnb29nbGUuY29tX2Qzb3Zjdm8xcDMyMTloOTg5NTczdjk4Zm5zQGc&tmsrc=google.com_d3ovcvo1p3219h989573v98fns%40group.calendar.google.com&scp=ALL) |
| Meeting Notes              | [Notes](https://docs.google.com/document/d/1bG4mbjycmFtIBezA6AJoQvaB4-v3874dhX7n-DhGAx0/edit)                                                                                                                                             |
| Document Folder            | [Folder](https://drive.google.com/drive/folders/1SCS7q9Ns9m8p7MG_4URiFKirz1SgID_B)                                                                                                                                                        |
| Slack Channel              | [#dashboard](https://tektoncd.slack.com/messages/dashboard)                                                                                                                                                                                 |


| &nbsp;                                                        | Facilitators    | Company | Profile                                            |
| -----------------------------------------------------------   | ----------      | ------- | ------------------------------------------------   |
| <img width="30px" src="https://github.com/a-roberts.png">     | Adam Roberts    | IBM     | [a-roberts](https://github.com/a-roberts)          |
| <img width="30px" src="https://github.com/mnuttall.png">      | Mark Nuttall    | IBM     | [mnuttall](https://github.com/mnuttall)            |
| <img width="30px" src="https://github.com/skaegi.png">        | Simon Kaegi     | IBM     | [skaegi](https://github.com/skaegi)                |
| <img width="30px" src="https://github.com/dibbles.png">       | Duane Appleby   | IBM     | [dibbles](https://github.com/dibbles)              |
| <img width="30px" src="https://github.com/steveodonovan.png"> | Steve O'Donovan | IBM     | [steveodonovan](https://github.com/steveodonovan)  |
| <img width="30px" src="https://github.com/AlanGreene.png">    | Alan Greene     | IBM     | [AlanGreene](https://github.com/AlanGreene)        |
