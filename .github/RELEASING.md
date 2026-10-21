# Releasing this repository on GitHub

The host-specific commands for the steps in `MAINTAINING.md`. They stay in
the kit's repository and are never installed into a project.

Run the native platform workflow on the candidate commit and wait for all
four jobs to pass:

```sh
gh workflow run native-platforms.yml --ref main
gh run watch "$(gh run list --workflow native-platforms.yml --limit 1 --json databaseId --jq '.[0].databaseId')" --exit-status
```

After pushing `main` and the annotated tag, publish its release with the
changelog section as the notes. The newest release is marked latest:

```sh
python3 tests/release_notes.py X.Y.Z > NOTES.md
gh release create vX.Y.Z --verify-tag --title X.Y.Z --notes-file NOTES.md
```

A release page never replaces the tag: projects install and verify the tag
and its `RELEASE.json`, so deleting a page changes nothing they installed.
