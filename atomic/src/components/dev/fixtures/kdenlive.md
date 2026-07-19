# State of Kdenlive - 2026

In 2025, the Kdenlive team continued grinding to push the project forward through steady development, collaboration, and community support\. Over the past year we’ve found a nice balance between adding new features, bug fixing, polishing the user interface, and improving performance and workflow, with stability taking priority over feature creep\.

We relaunched the website with a new content management system, refreshed some content and the design, and restored historic content dating back to 2002\. We also strengthened upstream collaboration with the MLT developers and contributed several improvements to OpenTimelineIO\.

Here’s a look at what we've been up to and what is ahead\.

## RELEASE HIGHLIGHTS

As part of [KDE Apps](https://apps.kde.org/), we follow the KDE Gear [release cycle](https://community.kde.org/Schedules), with three major releases each year—in April, August, and December—each followed by three point maintenance releases\.

### 25\.04\.0

This release added a powerful automatic masking tool and brought the last batch of features from our last fundraiser\.

[-\> Read full changelog](https://kdenlive.org/news/releases/25.04.0/)

### Background Removal

The new Object Segmentation plugin based on the \[SAM2\]\[4\] model allows to remove any selected object from the background\.

### OpenTimelineIO

![otio](https://kdenlive.org/news/2026/state-2026/otiov.png)

We rewrote our OpenTimelineIO import and export function using the C\+\+ library\. Now you can exchange projects with other editing applications that support this open source file format\.

### Waveform improvements

![waveforns](https://kdenlive.org/news/2026/state-2026/waves.png)

Audio waveform generation got a 300% performance boost, along with a refactored sampling method that accurately renders the audio signal and higher-resolution waveforms for greater precision\.

### 25\.08\.0

This release focused heavily on stabilization, bringing over 300 commits and fixing more than 15 crashes\. Instead of major new features, the effort went into polishing and bug fixing\.

[-\> Read full changelog](https://kdenlive.org/news/releases/25.08.0/)

### Audio Mixer

![mixer](https://kdenlive.org/news/2026/state-2026/mixer.png)

We redesigned the audio mixer bringing levels with clearer visuals and thresholds\. We also did some code refactoring and cleanup\. This change fixes issues with HiDPI displays with fractional scaling\.

### Markers and Guides

Guides and Markers got a major overhaul this release to improve the project organization\.

### Titler improvements

This release the titler received some much needed love like improved SVG and image support with ability to move and resize items, added center resize with Shift \+ Drag, and renamed the Pattern tab to Templates and moved the templates dropdown to it

### 25\.12\.0

The focus of this release cycle was on improving the user experience and polishing the user interface\.

[-\> Read full changelog](https://kdenlive.org/news/releases/25.12.0/)

### Welcome Screen

![welcome_screen](https://kdenlive.org/news/2026/state-2026/welcome.webp)

We added a new first-run launch screen for first time users as well as added a Welcome Screen allowing to easily launch recent projects\.

### Docking System

We added a new, more flexible docking system that lets you group widgets, show or hide them on demand, and save layouts as separate files that can be shared or stored within projects\.

### Redesigned monitor

The audio waveform in the Project Monitor got a revamped interface with an added minimap\.

## THE ROAD AHEAD

### 26\.04

This next release is just around the corner and brings a nice batch of nifty new features like monitor mirroring and animated transition previews, making it much easier to visualize how they will look before applying them\. Additionally, dropping a transition onto the timeline can now automatically adjust its duration to match the clips above and below, saving time and reducing manual tweaking\.

This feature allows you to mirror any monitor while working in fullscreen mode\. It’s especially useful when working with multiple displays or collaborating with others in the editing room\.

#### OTHER NOTEWORTHY FEATURES

- Change the playback speed of multiple clips at once
- Import a clip directly from the timeline context menu and insert it at the click position
- Option to always zoom toward the mouse position instead of the timeline playhead
- Generate audio thumbnails for sequences

### ROADMAP

Our [roadmap](https://kdenlive.org/roadmap/) is constantly being reviewed and updated, and some of the upcoming highlights include implementing the new features in MLT, the multimedia framework which powers Kdenlive\. Some exciting upcoming features include 10/12 bit color support, [playback optimizations \(decoding\)](https://github.com/mltframework/mlt/commit/799b222aa0e2432269032193816d7565e2d8984f), and [OpenFX](https://github.com/mltframework/mlt/commit/fa0622a7dc826aaa842215c0f43522cfac5a68aa) support\. *\(Shoutout to a Kdenlive community member for leading this effort\)*\. Also expected is a refactoring of the subtitle system as well as continuing to develop the *Advanced Trimming Tools*\.

#### DOPESHEET

We are currently working on refactoring the keyframing system and implementing a Dopesheet, basically it is a dedicated timeline for managing and viewing keyframes from multiple effects simultaneously\. This work will also introduce per-parameter keyframing \(currently, once you add a keyframe to an effect, it is applied to all parameters by default\)\. More info can be found in the last [status report](https://kdenlive.org/news/2026/dopesheet-status-1-26/)\. This work is made possible through an [NGI Zero Commons grant via NLnet](https://nlnet.nl/project/Kdenlive/)\.

![dopesheet](https://kdenlive.org/news/2026/state-2026/dopesheet.png)

#### MICROSOFT STORE

We have been working on [enabling and fixing](https://github.com/mltframework/mlt/commits/master/?author=jlskuz) multiple modules in MLT to compile with MSVC allowing us to ship Kdenlive in the Microsoft Store soon\. Another advantage is that it will allow to run unit tests on our [CI for Windows\.](https://invent.kde.org/multimedia/kdenlive/-/merge_requests/721)

![Community](https://kdenlive.org/news/2026/state-2026/community2.png)

### NEW CONTRIBUTORS

Currently, the Kdenlive core team is made up of 8 active members, including 2 developers\.

In 2025, 38 people contributed code to Kdenlive \(including the core dev team and other KDE devs\), a truly impressive number\! Even more exciting, about half of them were first-time contributors, which is always great\. We hope to see many of them continue contributing in the future\. On behalf of the Kdenlive team, we salute you all\!

List of contributors and commits

*Note that these numbers refer specifically to contributions to the Kdenlive application\. Other projects such as the test suite and website are hosted in separate repositories and are not included in these figures\.*

- 878 — Jean-Baptiste Mardelle *\(core team\)*
- 126 — balooii balooii
- 109 — Julius Künzel *\(core team\)*
- 60 — Darby Johnston *\(fundraiser\)*
- 26 — Bernd Jordan *\(core team\)*
- 24 — Ajay Chauhan
- 11 — Eugen Mohr *\(core team\)*
- 9 — Scarlett Moore *\(KDE\)*
- 8 — Yuri Chornoivan *\(KDE\)*
- 7 — Justin Zobel *\(KDE\)*
- 7 — Ron Lee *\(core team\)*
- 6 — Farid Abdelnour *\(core team\)*
- 5 — Josep M\. Ferrer
- 5 — Étienne André *\(fundraiser\)*
- 4 — Kunda Ki
- 4 — Swastik Patel
- 3 — Camille Moulin *\(core team\)*
- 3 — Carlos De Maine
- 2 — Johnny Jazeix *\(KDE\)*
- 2 — Luigi Toscano *\(KDE\)*
- 2 — Nicolas Fella *\(KDE\)*
- 2 — Richard Ash
- 2 — Side Projects Lab
- 2 — Xander Bailey
- 2 — chocolate image
- 1 — Adam Fidel
- 1 — Alex Efimov
- 1 — Edward McVern
- 1 — Eli George
- 1 — Helga K
- 1 — Jack Bruienne
- 1 — Jonas Endter
- 1 — Oliver Kellogg
- 1 — Rafael Sadowski
- 1 — Steve Cossette

### SPRINTS AND EVENTS

#### AMSTERDAM SPRINT

![Amsterdam sprint](https://kdenlive.org/news/2026/state-2026/kdenlive-blender.jpg)

In February, part of the Kdenlive core team met in [Amsterdam for a short sprint](https://kdenlive.org/news/2025/amsterdam-sprint-report/), highlighted by a visit to the Blender Foundation, where we met with Francesco Siddi and he shared valuable insights into Blender’s history and offered advice on product management for Kdenlive\. We also attended their weekly open session, where artists and developers present progress on ongoing projects\. During the sprint, we discussed and advanced several technical topics, some highlights include:

- Refining the audio workflow task
- Developing a proof of concept to improve clip timecode handling
- Finishing an MLT Framework patch to enable rendering without a display server \(needed for Flatpak testing\)

#### BERLIN SPRINT

![Kdenlive Berlin](https://kdenlive.org/news/2026/state-2026/kdenlive-berlin.jpg)

The [Berlin sprint](https://kdenlive.org/news/2025/berlin-sprint/) was one of our most productive gatherings to date\. Most of the team was there in person, and we also connected online with those who couldn’t make it\. We discussed just about every aspect of the project, from roadmap planning to upcoming features and workflow improvements\. Some of the highlights include:

- Evaluated the current state of the Titler and discussed possible integration with Glaxnimate
- Reorganized the Menu structure
- Developed a proof of concept for using KDDockWidgets
- Redesigned and started development of the audio clip view in the Clip Monitor

Thanks to the nice folks at [c-base](https://c-base.org/) who kindly hosted us\.

#### AKADEMY 2025

![Akademy](https://kdenlive.org/news/2026/state-2026/akademy.jpg)

Akademy is always a great opportunity to exchange ideas with the broader KDE and Qt communities\. One of the highlights was meeting the maintainer of Glaxnimate, where we discussed common goals and ways to collaborate\. This year, [Akademy will be in Graz](https://akademy.kde.org/2026/) on the 19-24 of September, and we hope to see you there\.

### SHOWCASE

We’re very happy to see more YouTube channels talking about Kdenlive\. Here are some examples of what the community has been creating\.

We'd love to see what you've been working on in the past year\. Share your videos productions in the comments\!

### SPREAD THE WORD

Help us grow the community by organizing meetups, talks, or workshops in your local area\. Don’t hesitate to contact us if you need guidance, materials, or support to get started\.

Below are photos from a workshop with indigenous communities in Paraguay\.

![Screenshot of <nil>](https://kdenlive.org/news/2026/state-2026/w1.jpg)

![Screenshot of <nil>](https://kdenlive.org/news/2026/state-2026/w2.jpg)

![Screenshot of <nil>](https://kdenlive.org/news/2026/state-2026/w3.jpg)

### STATS

#### DOWNLOADS

- Kdenlive was downloaded 11,500,714 times from our download page in 2025\. Do note that many additional installs happen through Linux distribution package managers, the Snap Store, Flathub, and other third-party servers, where statistics are not always available or reliably measurable\.
- The Flatpak package from [Flathub](https://flathub.org/en/apps/org.kde.kdenlive) gets 41,499 downloads per month\.
- 25\.04\.2 got the most number of downloads\.
- 17\.08\.2 was downloaded 1 time\!

**Downloads per release cycle**

Windows Linux Mac

#### CODE COMMITS

**Per Release Cycle**

- 25\.04 cycle: 403 commits
- 25\.08 cycle: 368 commits
- 25\.12 cycle: 405 commits

**Files With Most Code Changes**

- src/mainwindow\.cpp: 102 commits
- src/bin/bin\.cpp: 70 commits
- src/timeline2/view/timelinecontroller\.cpp: 67 commits
- src/monitor/monitor\.cpp: 60 commits
- data/org\.kde\.kdenlive\.appdata\.xml: 57 commits

**Files With Most Bug Fixes**

- src/mainwindow\.cpp: 1021 commits
- src/timeline2/model/timelinemodel\.cpp: 600 commits
- src/bin/bin\.cpp: 593 commits
- src/timeline2/view/timelinecontroller\.cpp: 506 commits
- src/renderer\.cpp: 501 commits

#### USERBASE

**Continent**

- 🌍 Europe — 949,077
- 🌎 Americas — 781,131
- 🌏 Asia — 750,406
- 🌍 Africa — 127,948
- 🌏 Oceania — 53,397
- 🧊 Antarctica — 5

*To the 5 of you in Antarctica, let us know what you are editing\. ;\)*

**Country**

- 🇺🇸 United States — 392,967
- 🇮🇳 India — 267,449
- 🇧🇷 Brazil — 153,319
- 🇩🇪 Germany — 118,115
- 🇫🇷 France — 111,071
- 🇨🇳 China — 104,692
- 🇷🇺 Russia — 96,051
- 🇪🇸 Spain — 91,052
- 🇬🇧 United Kingdom — 86,165
- 🇮🇹 Italy — 61,814

**Region**

- 🇺🇸 California, United States — 42,769
- 🇧🇷 São Paulo, Brazil — 37,452
- 🇮🇳 Tamil Nādu, India — 27,313
- 🇫🇷 Île-de-France, France — 26,755
- 🇮🇳 Mahārāshtra, India — 25,246
- 🇺🇸 Texas, United States — 22,470
- 🇨🇦 Ontario, Canada — 20,016
- 🇳🇱 Noord-Holland, Netherlands — 19,826
- 🇺🇸 Florida, United States — 18,997
- 🇨🇳 Shanghai Shi, China — 18,991

#### FUNDING

Ever since our last, and [very successful](https://kdenlive.org/news/2025/fundraising-final-report/), fundraiser in 2022, we haven’t actively asked for donations, yet the community has continued to support us\. We are very grateful for that\.

In 2025, we received a total of €9,344\.80 from donations \(down from €11,526\.61 in 2024\)\. Around 30% of the amount was given by donors who kindly set up a recurring plan\. The average donation was about €25, with the lowest amount being €10 and the highest €500\.

We allocate 20% of our budget to [KDE e\.V\.](https://ev.kde.org/) to support infrastructure costs \(servers and related expenses\), as well as administration, legal support, and travel\. As in previous years, your contributions enable us to continue supporting Jean-Baptiste \(Kdenlive's maintainer\), allowing him to dedicate several days each month to Kdenlive in addition to his volunteer work\.

## WE **NEED** YOUR SUPPORT

Kdenlive needs your support to keep growing and improving\. If just a quarter of the people who downloaded Kdenlive in 2025 contributed €5, our maintainers would be able to dedicate more time to the project, and it would even allow us to hire more develpers to speed up development and improve stability\. Small amounts can make a big difference, please consider making a donation\.

[More options to donate](https://kdenlive.org/fund/)

You may also contribute by getting involved and helping in:

- [Reporting](https://kdenlive.org/bug-reports/), debugging, and [triaging bugs](https://community.kde.org/Guidelines_and_HOWTOs/Bug_triaging)
- [Translating](https://community.kde.org/Get_Involved/translation) Kdenlive in your language
- Promote Kdenlive in your local community
