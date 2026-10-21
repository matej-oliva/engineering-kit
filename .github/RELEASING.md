# Releasing this repository on GitHub

The host-specific commands for the steps in `MAINTAINING.md`. They stay on
the kit's branches and are never in a release tag or a project.

Run the native platform workflow on the candidate commit with the release
rehearsal, and wait for all four jobs to pass:

```sh
gh workflow run native-platforms.yml --ref main -f candidate=X.Y.Z
gh run watch "$(gh run list --workflow native-platforms.yml --limit 1 --json databaseId --jq '.[0].databaseId')" --exit-status
```

Make the release commit and tag with `python3 tests/release_commit.py X.Y.Z`,
push the tag alone with `git push origin vX.Y.Z`, then publish its release
page with the changelog section as the notes. The newest release is marked
latest:

```sh
python3 tests/release_notes.py X.Y.Z > NOTES.md
gh release create vX.Y.Z --verify-tag --title X.Y.Z --notes-file NOTES.md
```

Then run the workflow again without a candidate. Its lifecycle step installs
the previous published release and updates it to the new tag on each
platform.

A release page never replaces the tag: projects install and verify the tag
and its `RELEASE.json`, so deleting a page changes nothing they installed.
