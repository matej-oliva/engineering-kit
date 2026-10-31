# Maintenance and contributions

[Guide](README.md) · The kit improves from what its projects learn. This
page covers keeping a project current and sending a lesson back.

## Keep a project current

When a release appears, and at least once a month, read its notes and
preview it:

```sh
python3 kit update --diff
```

Apply it when the preview shows what you expect, run `python3 kit check`,
review and commit. The newest release and the one before it are supported,
and a security fix ships as a patch release within seven days of the
finding, or the changelog names a workaround until it does
([`MAINTAINING.md`](../MAINTAINING.md)). Staying within one release of the
newest keeps a project supported.

This guide is part of each release. An update replaces it with the guide of
the new release, so the guide in your project always describes the kit you
have installed. Edits you make to it are merged like edits to any kit file,
but a project's own notes belong in `project.json` or its own
documentation instead.

## Moving to this release, 1.4.0

Each release rewrites this section for itself; the changelog keeps what
every earlier release asked.

From 1.3.0, 1.2.1 or 1.2.0, `python3 kit update --apply` is enough, or without the launcher
`python3 .engineering-kit/kit/tools/kit.py update --apply`. From 1.1.0 the
long form does the same. From 1.0.1, 1.0.0 or a pilot release, name the
version once: `python3 .engineering-kit/kit/tools/kit.py update 1.4.0
--apply`. The contract is unchanged and nothing else is required. This
release adds the optional `work-cycle` integration, which installs nothing
until you enable it with its five permissions, as
[Customize](customize.md) lists; its setup guide is `.kit-cycle/guide.md`
once installed. Coming from 1.2.1 or earlier with `agent-skills` enabled,
updating also adds `kit-grill-me`, an interview that starts only when you
ask for it by name. See [Skills](skills.md) for usage and client limitations.
To get the short command and the skills, add these
to `integrations` in `project.json` and update again:

```json
"launcher": {"grant": ["writes-launcher"]},
"agent-skills": {"grant": ["writes-skills"]}
```

Once you grant `launcher` or `agent-skills`, rolling back to a release
without them needs that grant removed first, as
[Troubleshooting](troubleshooting.md#a-release-lacks-an-integration-you-granted)
explains.

## Send a lesson back

A change you made to a kit file, or something your project learned that
other projects could use, can become part of the kit.
[`procedures/contribute.md`](../procedures/contribute.md) has the steps. In
short: say what need or failure it answers, what evidence shows it works,
its limits, who owns it and whether you have the right to share it. The kit
prepares the patch and a contribution record:

```sh
python3 kit contribute .engineering-kit/kit/procedures/review.md --out ../lesson \
  --need "Reviews missed ..." --evidence "Task T-31 ..." --limits "Only for ..." \
  --rights owner-authored --owner "Dana Ruiz"
```

`--rights` is `owner-authored` for your own work, `licensed:` followed by
the licence's SPDX identifier, such as `licensed:MIT`, or `cleared:`
followed by a reference to the clearance you hold.

The kit's maintainer applies the patch in the kit's repository, reviews it
like any change and releases it. Material from an employer, client or third
party stays out unless its owner cleared it.

## Decisions worth recording

Record a decision in the task, or in your project's own decision log, when
it is hard to reverse, surprising to a newcomer, and a real trade-off. Most
choices are none of these and need no record beyond the task itself.
