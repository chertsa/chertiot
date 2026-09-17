# Master Prompt — Install Arabic (`ar-AR`) in Node-RED as a Standard LTR Language

## Role

You are the senior Node-RED maintainer responsible for adding Arabic as a first-class, permanent editor language while preserving Node-RED's existing **left-to-right (LTR)** interface and layout.

## Owner decision — binding scope

The owner has explicitly decided:

> Add the Arabic language only. Keep the complete Node-RED editor LTR. Do not implement RTL.

This decision is mandatory:

- Arabic text must display inside the existing LTR interface.
- The page, menus, sidebars, forms, dialogs, palette and flow editor must remain LTR.
- Do not set `dir="rtl"` on `<html>`, `<body>` or application containers.
- Do not mirror components, icons, ports, canvas coordinates or navigation.
- Do not add RTL stylesheets or `[dir="rtl"]` layout rules.
- Do not convert physical CSS properties to RTL logical layouts as part of this task.
- Do not expand this task into general RTL support.

The required result is **Arabic localization in an LTR Node-RED editor**.

## Non-negotiable implementation standard

This must be a canonical, source-controlled Node-RED language addition—not a temporary patch or runtime workaround.

Do not implement this by:

- modifying a globally installed Node-RED package;
- editing `/usr/lib/node_modules`, `/usr/local/lib/node_modules` or generated application `node_modules`;
- copying files into a running container;
- mounting a locale folder with Docker or Kubernetes;
- using an init container or startup script to inject files;
- using `postinstall` to rewrite a dependency;
- applying an uncommitted server patch;
- modifying browser storage manually;
- hiding untranslated content with CSS.

The Arabic catalogs must live in the canonical Node-RED source or an approved maintained fork, be committed, tested, built and included in the normal immutable deployment artifact.

## Governance requirements

Before making changes:

1. Inspect the repository, branch, working tree, Node-RED version, build system and deployment method.
2. Record the exact upstream release tag and full commit SHA.
3. Confirm that this is the canonical Node-RED source repository or approved long-lived fork.
4. Preserve all unrelated user changes.
5. Do not change Node-RED, Node.js or dependency versions unless required and explicitly approved.
6. Do not claim completion from file presence alone; prove discovery, selection, catalog loading, persistence, fallback, packaging and runtime survival after restart.
7. Produce:
   - a prompt/task record;
   - an implementation response/evidence report;
   - a project tracker update.

If the repository is not the canonical source/fork, stop and report the correct repository and branch. Do not patch the deployed installation.

## Objective

Add **Arabic (`ar-AR`)** to Node-RED as a standard editor language with:

- source-controlled translation catalogs;
- automatic discovery through the existing Node-RED i18n mechanism;
- an Arabic entry in the standard language selector;
- persistence through the existing `editor-language` preference;
- `en-US` fallback for future missing translations;
- correct rendering of Arabic and mixed Arabic/English text;
- unchanged LTR application direction and layout;
- automated catalog-integrity tests;
- a reproducible package or container build;
- an immutable deployable artifact;
- documented upgrade and maintenance rules.

## Approved Arabic catalogs

The supplied translation package contains:

```text
ar-AR/
├── editor.json
├── infotips.json
└── jsonata.json
```

Use these supplied catalogs as the approved translation source. Locate them in the task attachments or project audit directory. Do not regenerate them from English and do not silently replace Arabic values.

If the supplied `ar-AR` folder is unavailable, stop and report the missing input.

## Required implementation

### 1. Confirm canonical locale paths

Verify the paths against the checked-out Node-RED revision. The expected permanent destinations are:

```text
packages/node_modules/@node-red/editor-client/locales/ar-AR/editor.json
packages/node_modules/@node-red/editor-client/locales/ar-AR/infotips.json
packages/node_modules/@node-red/editor-client/locales/ar-AR/jsonata.json
```

These paths are part of the Node-RED monorepo source even though their path contains `node_modules`. Distinguish them from generated or installed dependency directories. Only the repository-owned source path is valid.

Copy the approved catalogs into the confirmed canonical source path and commit them normally.

### 2. Reconcile against the exact target revision

Recursively compare each Arabic file with the matching `en-US` file from the target revision.

Validate:

- valid UTF-8 JSON without BOM;
- identical object structure and key set, except documented language-metadata additions;
- identical value types;
- no missing translation keys;
- no unexpected keys;
- preservation of Node-RED interpolation tokens such as `__name__`, `__error__` and `__count__`;
- preservation of i18next/action tokens such as `{{core:search}}`;
- preservation of HTML tags and entities;
- preservation of URLs and paths;
- preservation of JSONata function names and argument signatures;
- preservation of keyboard tokens such as `[ctrl]`, `[shift]`, `[left]` and `[right]`;
- preservation of JSON keys, MQTT topics, protocol identifiers and executable expressions;
- absence of temporary translation markers or malformed Unicode.

If upstream added English keys after the Arabic files were prepared, translate only those new keys into professional Modern Standard Arabic. Preserve all protected tokens and list the added keys in the evidence report.

### 3. Register `ar-AR` through Node-RED's standard discovery mechanism

Node-RED uses its normal i18n catalog discovery to populate available editor languages. Follow that mechanism. Do not create a Chert-specific secondary language selector or hard-coded parallel list.

Add the Arabic language label through the existing `languages` catalog object:

```json
"ar-AR": "العربية"
```

Ensure that:

- `ar-AR/editor.json` includes `languages.ar-AR`;
- `en-US/editor.json` includes an `ar-AR` language label for fallback;
- other existing locale catalogs are updated only if the existing Node-RED convention requires every language label in every catalog;
- `i18n.availableLanguages("editor")` returns `ar-AR`;
- the runtime settings API includes `ar-AR` in `editorTheme.languages`;
- the standard language selector displays `العربية`;
- selecting Arabic uses the existing `editor-language=ar-AR` preference;
- reloading the editor preserves Arabic;
- a new authenticated session preserves the supported preference according to current Node-RED behavior;
- browser locale detection can choose `ar-AR` when there is no explicit preference;
- unsupported Arabic regional variants fall back deliberately to `ar-AR` only if this matches the existing i18next resolution policy;
- missing Arabic keys fall back to `en-US` rather than rendering raw key names.

Update the sample `settings.js` supported-language comment and any official language inventory present in the target revision.

### 4. Enforce the LTR-only owner decision

Arabic selection must not alter application direction.

Required behavior when Arabic is selected:

```html
<html lang="ar-AR" dir="ltr">
```

If the current application does not explicitly set `dir`, leaving its established LTR behavior intact is acceptable. Set `lang="ar-AR"` through the normal language lifecycle if Node-RED already manages the document language or if accessibility requires it.

Do not:

- set `dir="rtl"` anywhere globally;
- mirror the header, main menu, palette or sidebar;
- move form labels or buttons;
- reverse tables, tabs, breadcrumbs or pagination;
- mirror the flow workspace;
- reverse node ports or connections;
- modify Monaco or Ace editor direction;
- add RTL-specific CSS;
- introduce a direction toggle.

Arabic labels should render naturally as Unicode text inside the existing LTR components. Node-RED's existing bidirectional text utilities may continue handling mixed content; do not rewrite or replace them.

Keep these technical surfaces explicitly or inherently LTR:

- code editors;
- JSON and JSONata editors;
- regular expressions;
- MQTT topics;
- URLs and file paths;
- IP addresses and ports;
- node IDs and property identifiers;
- environment-variable names;
- logs, stack traces and terminal output;
- Git hashes and version strings.

Do not insert Unicode direction-control characters into translation strings or stored user data.

### 5. Add automated catalog tests

Add a maintainable validation test or repository script that fails CI when Arabic drifts from `en-US`.

Required checks:

1. Parse all three Arabic JSON files.
2. Recursively compare key paths and value types against `en-US`.
3. Compare interpolation tokens per key.
4. Compare i18next action tokens per key.
5. Compare embedded HTML tags, entities and URLs per key.
6. Assert unchanged JSONata `args` signatures.
7. Assert absence of translation sentinels and malformed Unicode.
8. Assert `languages.ar-AR` exists in the required catalogs.
9. Assert standard language discovery returns `ar-AR`.
10. Assert English fallback works for a deliberately missing test key.
11. Assert selecting Arabic does **not** produce `dir="rtl"` or activate RTL styles.
12. Run the existing Node-RED lint, unit and build checks for every modified package.

Use the project's existing testing conventions and frameworks. Do not introduce an unrelated test stack for this change.

### 6. Add browser-level acceptance coverage

Using the repository's supported browser-test framework, verify:

- Arabic appears in the standard language selector;
- selecting it loads the Arabic catalogs without 404 responses;
- the preference persists across reload;
- the document language reports `ar-AR` where supported;
- the document and application remain LTR;
- the header, menus, palette, flow canvas and sidebar retain their original positions;
- Arabic labels render without broken glyphs or replacement characters;
- mixed Arabic/English labels remain readable;
- JSON, JSONata, MQTT topics and URLs remain LTR;
- import, export, node editing and deployment still work;
- switching back to English works without stale Arabic content;
- no console errors or failed locale requests occur.

Capture screenshots of:

1. the language selector containing `العربية`;
2. the Arabic editor in its unchanged LTR layout;
3. Arabic node or dialog labels alongside LTR technical values;
4. the editor after switching back to English.

### 7. Build a permanent release artifact

Build Node-RED from the committed source using the repository's supported release process.

For container deployment:

- build an immutable image from the approved fork and commit;
- use a versioned image tag;
- record the image digest;
- verify that `locales/ar-AR/*.json` exists in the packaged editor client;
- update the normal deployment manifest to use the immutable image reference;
- preserve flows, credentials, settings and persistent volumes;
- use the established rollout and rollback procedure;
- never copy locale files into the running container.

For npm/package deployment:

- build and pack the repository workspace packages normally;
- inspect the package archive and prove the three `ar-AR` catalogs are included;
- install the versioned package through the normal dependency and lockfile workflow;
- never mutate the installed package after installation.

### 8. Runtime acceptance and durability proof

After deployment, prove against the actual running instance:

- `ar-AR` is advertised by the normal runtime settings API;
- `العربية` appears in the normal language selector;
- the three Arabic catalogs are served through the normal locale endpoint;
- selecting Arabic loads translated labels;
- the layout remains LTR;
- the flow canvas remains unchanged;
- technical content remains LTR;
- preference persists after browser reload;
- English fallback operates correctly;
- switching back to English restores English normally;
- Node-RED flow editing and deployment remain functional;
- a service restart retains Arabic;
- a container replacement or clean redeployment from the same artifact retains Arabic;
- no runtime file-copy or patch step is required.

## Maintenance and upgrade policy

1. Keep Arabic catalogs in the approved Node-RED fork until accepted upstream.
2. Rebase or merge upstream through normal review.
3. Run Arabic/English catalog parity checks whenever an `en-US` catalog changes.
4. Block release if English adds keys that Arabic lacks or protected tokens diverge.
5. Maintain Arabic as LTR unless the owner explicitly approves a separate future RTL project.
6. Keep localization commits logically separated from unrelated branding or feature work.
7. Prepare an upstream-ready commit or pull request consistent with Node-RED contribution requirements.

Recommended commit separation:

1. Arabic catalogs and language registration.
2. Catalog validation tests.
3. Documentation and supported-language inventory.

No RTL commit is authorized.

## Required evidence report

Create:

```text
docs/audit/node-red-arabic-ltr-standard-installation-report.md
```

The report must include:

- repository and branch;
- upstream base tag and full SHA;
- Node-RED and `@node-red/editor-client` versions;
- exact changed-file list;
- source path of the approved Arabic catalogs;
- catalog key and value counts;
- parity and protected-token validation results;
- explanation of normal language discovery;
- proof that `ar-AR` appears in runtime settings;
- proof of language selection and persistence;
- proof that the application remained LTR;
- lint, unit, browser and build commands with exit codes;
- immutable package/image identifier and digest;
- deployment manifest change;
- runtime endpoint and screenshot evidence;
- restart and clean-redeployment evidence;
- known translation limitations, if any;
- rollback procedure;
- implementing commit and upstream PR reference, if created.

Update the project tracker with final status and links to the report and commit.

## Stop conditions

Stop and report without applying a workaround if:

- the canonical repository or approved branch cannot be identified;
- the approved Arabic catalogs are missing;
- catalog differences cannot be reconciled safely;
- implementation would require modifying a generated or installed dependency;
- the build or relevant test suite fails because of the change;
- deployment would require changing files inside a running container;
- permissions or production approval are missing;
- unrelated changes overlap the required files and cannot be preserved;
- any requested change would introduce RTL contrary to the owner decision.

## Final response format

Return:

1. **Verdict** — completed, partially completed or blocked.
2. **Canonical implementation** — repository, branch, commit and source paths.
3. **Catalog validation** — counts, parity and token results.
4. **Language registration** — discovery, selector and persistence proof.
5. **LTR proof** — evidence that Arabic did not change layout direction.
6. **Tests** — commands, exit codes and results.
7. **Build and deployment** — immutable artifact and deployed revision.
8. **Runtime durability** — reload, restart and clean-redeployment results.
9. **Limitations or blockers** — explicit and honest.
10. **Artifacts** — audit report, tracker update, screenshots and commit/PR.

Do not say “done” unless Arabic is committed in canonical source, included in a reproducible build, deployed through the normal release process, verified as LTR after restart and clean redeployment, and documented in the required evidence report.
