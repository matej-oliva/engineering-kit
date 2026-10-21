# Maintaining the kit

The repository owner maintains the kit. Agents prepare changes and releases;
the owner approves anything that widens what the kit may write or do.

## Versions and support

- A release is an annotated tag `vMAJOR.MINOR.PATCH` on the commit holding
  its `RELEASE.json`. A published tag never moves: projects refuse a tag
  that no longer matches what they installed.
- PATCH releases fix defects and wording. MINOR releases add procedures,
  integrations or checks, including checks that refuse records an earlier
  release accepted; the changelog lists them. MAJOR releases change the
  contract version, which projects accept with `--accept-contract`.
- The latest release and the one before it are supported. A security fix
  ships as a PATCH of the latest release within seven days of the finding,
  or the changelog names a workaround until it does.
- Projects review their installed version when a release appears and at
  least once a month, by reading `CHANGELOG.md` and previewing the update.

## Making a release

1. Every change since the last release has passed
   `python3 -m unittest discover -s tests` and
   `python3 tests/windows_text_mode.py`, and
   `python3 tests/mutation_check.py` reports every mutant caught. Add a
   mutant whenever you add a guard. The release rehearsal passes:
   `python3 tests/native_release.py --source . --candidate X.Y.Z --report
   REPORT` cuts the release in a scratch clone, then installs each of the
   two newest published releases with its own tool and updates it to the
   candidate. Older updaters read every new release, so only this shows
   they accept it. The manually started native platform workflow passes the
   same rehearsal on the candidate commit; the repository's host-specific
   commands are in `.github/RELEASING.md`.
2. A fresh reviewer who did not write the changes reviews
   `git diff vPREVIOUS..HEAD` against the commit messages. Blocking findings
   are fixed and reviewed again, by a reviewer given the earlier findings.
3. `CHANGELOG.md` says what changed, what a project must do after updating,
   and whether the contract changed. The guide in `guide/` describes the
   release's behaviour, including its moving-to section in
   `guide/maintenance.md`, and every diagram still matches its prose.
4. Commit every kit file, push `main`, then run
   `python3 tests/release_commit.py X.Y.Z`. On a local branch
   `release/X.Y.Z` it leaves out repository-host files such as `.github/`,
   which earlier updaters would count as kit files, writes and checks
   `RELEASE.json`, and makes the annotated tag `vX.Y.Z`. `release` itself
   refuses uncommitted kit files and anything earlier updaters would
   misread. Push the tag alone; `RELEASE.json` exists only in tagged
   commits. Publish the Git host's release page for that tag, with its
   changelog section as the notes. The tag stays the release; the page
   announces it.
5. Install the release from the repository into a throwaway project with
   the commands in `README.md`, run `kit.py check`, and remove it again.
   Update a project on the previous release with its installed tool too.

## Contributions

Lessons arrive through `procedures/contribute.md` as a patch and a
contribution record. Check the record with `tools/kit.py check-contribution`,
apply the patch, add a check or conformance case where the lesson is
mechanical, and release it like any change. Material without stated rights,
or belonging to an employer or client without clearance, stays out.

## Recovery

- A defective release: publish a fixed PATCH. Projects that already updated
  return with `tools/kit.py rollback`, which keeps their own changes. Never
  move or delete a published tag.
- An interrupted update in a project: `tools/kit.py recover`, as described in
  `procedures/adopt-and-update.md`.
- A lost repository: keep a full mirror in an independently backed-up
  location using `git clone --mirror KIT_ADDRESS BACKUP_PATH`. Refresh it
  with `git -C BACKUP_PATH remote update` while the source is available.
  The shallow adoption clone in the README is not a full recovery copy.
  Restore the mirror's branches and tags to a reviewed replacement remote;
  each project's lock names the commit and digest of its installed release,
  which must match before projects update. Backup custody and a restore test
  belong to the maintainer; no off-host recovery test is claimed here.
