# CHERT System Questionnaire

**For:** Claude Code, working inside one Chert system repository
**Output:** one file, `CHERT_MAP_<CODE>.md`, saved at the folder docs/metromap of this repository 

Every Chert system is a separate project and repository. Each system is built from **engines**: rebranded and customised open-source systems, plus in-house engines written by the Chert team. Together they work as one platform.

Answer every question below for **this repository only**. The same questionnaire is used for all 20 systems, so the answers can be combined into one metro map of the CHERT economy:

- **Line** = a system
- **Station** = a function inside the system
- **Interchange** = a function or data entity shared with another system
- **Route** = a business process that moves through several functions

## How to answer

- Read the code, configuration, deployment files, and documentation before answering.
- Do not change any code. Only create the output file.
- Write in plain business language. Use technical names only in the "Where in the repo" columns.
- If you cannot find an answer, write `unknown` and add it to section 10. Do not guess.
- After every answer, mark it **(confirmed)** if you saw it in the code, or **(assumed)** if you are inferring it.
- Never copy passwords, keys, tokens, or `.env` values.

## Reference: system codes

Use these codes whenever you mention a Chert system.

| Code | System | Code | System |
|---|---|---|---|
| E | ChertERP | Q | ChertReg |
| M | ChertMail | X | ChertXI |
| R | ChertRetail | C | ChertChain |
| B | ChertBell | N | ChertEngineering |
| P | ChertRepat | I | ChertBI |
| O | ChertOS | T | ChertIoT |
| S | ChertSatellite | Z | ChertResearch |
| F | ChertFleet | K | Chert Think Tank |
| G | ChertGo | H | ChertLearningHub |
| A | CHERT Academy | U | ChertClub |

---

## 1. Subject: what is this system?

Answer in a short paragraph for each question.

1.1 What is the system's name, code, and website?
1.2 What is it, in one sentence a business owner would understand?
1.3 What problem does it solve for a business?
1.4 Who uses it (types of business, and types of people inside them)?
1.5 How is it delivered: installed on the customer's own server (ChertBox), run by Chert as a private platform, or public?
1.6 What is its current status: live, in development, or planned?

## 2. Engines inside the system

List every engine in this system, both open-source and in-house.

| # | Engine | Type | Based on (upstream project and version) | Licence | Role of this engine in the system | How much Chert changed it | Where in the repo |
|---|---|---|---|---|---|---|---|
| 1 | | open-source, rebranded / in-house | | | | branding only / configuration / plugins added / core code changed | |

Then answer:

2.1 Which engine is the core of the system, and which engines support it?
2.2 What exactly was changed during rebranding (names, logos, colours, languages, Arabic support)?
2.3 Which engines could run on their own, and which only work together with another engine?

## 3. Functions inside each engine

For **each engine** from section 2, list the functions it provides. A function is something a user or another system can do with it, such as "Payroll", "Online store", "Dispatch", or "Issue certificate". These become the stations on the map.

**Engine: _name_**

| # | Function | What it does | Who uses it | Status (live / partial / planned) | Where in the repo |
|---|---|---|---|---|---|
| 1 | | | | | |

Repeat this table for every engine.

## 4. In-house modules

List the modules the Chert team wrote: plugins, extensions, services, apps, adapters, and scripts.

| # | Module | Added to which engine | What it adds or changes | Functions from section 3 it supports | Where in the repo |
|---|---|---|---|---|---|
| 1 | | | | | |

## 5. Roles

5.1 **User roles.** List every user role or permission group in the system.

| # | Role | What this person does | Functions they use |
|---|---|---|---|
| 1 | | | |

5.2 **Engine roles.** In one sentence each, explain the job each engine does inside the whole system. For example: "iDempiere is the transaction and accounting core; the payroll module adds Saudi payroll rules on top of it."

## 6. Processes

List the main end-to-end business processes that run through this system. These become routes on the map.

| # | Process | Steps, in order (function → function → function) | Engines involved | Other Chert systems involved (codes) | Status |
|---|---|---|---|---|---|
| 1 | e.g. Order to delivery | | | | |

Aim for the 5 to 10 processes that matter most to the business.

## 7. Entities (data)

List the main data this system stores or uses. Use these standard names where they fit, so they match across all systems:

Organization, User, Role, Person, Customer, Supplier, Employee, Product, PriceList, StockItem, Location, SalesOrder, PurchaseOrder, Invoice, Payment, JournalEntry, Shipment, DeliveryJob, Vehicle, BillOfMaterials, ProductionOrder, Design, Device, SensorReading, Message, Call, Campaign, WebPage, Document, Registration, Course, Assessment, Certificate, Request, Contribution, Member, Job, Box, Domain, Metric, Dataset.

If something important is missing from this list, add it with a one-line definition.

| # | Entity | Created and owned by (engine → function) | Also used by (functions in this system) | Shared with other Chert systems? (codes, and in which direction) |
|---|---|---|---|---|
| 1 | | | | |

## 8. Connections

8.1 **Inside the system.** How do the engines talk to each other?

| From (engine → function) | To (engine → function) | Data (entity) | How (API, webhook, queue, shared database, file, single sign-on) | Status |
|---|---|---|---|---|

8.2 **With other Chert systems.** Search the code for any reference to other Chert systems, their domains, or their APIs.

| From (this system: function) | To (system code: function) | Data (entity) | Direction (sends / receives / both) | How | Status (live / planned / idea) |
|---|---|---|---|---|---|

8.3 **With outside services.** For example payment gateways, SFDA, ZATCA, carriers, ad platforms, or SMS providers.

| Function | Outside service | Data | Direction | Status |
|---|---|---|---|---|

## 9. Overlaps with other Chert systems

List every function in this system that also exists, or probably exists, in another Chert system. For example: customer lists, product catalogues, user logins, email sending, invoicing, reporting. These become the interchanges on the map.

| Function here | Same function in (system codes) | Shared entity | Which system should own it (or "not decided") | Connected today? (yes / no / partly) |
|---|---|---|---|---|

## 10. Open questions

List everything you could not determine from the repository, as direct questions for the developer.

---

## Before you finish

- Every engine in section 2 has its functions listed in section 3.
- Every function belongs to exactly one engine.
- Every process in section 6 uses functions from section 3.
- Every entity in section 7 has an owner.
- Every mention of another system uses its code.
- No secrets appear anywhere.

Save the answers as `CHERT_MAP_<CODE>.md` at the repository root, for example `CHERT_MAP_E.md` for ChertERP. Then reply with a short summary: the number of engines, functions, processes, and entities you found, and the open questions.
