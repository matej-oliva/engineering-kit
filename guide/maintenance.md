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
and a security fix ships as a patch release, so staying within one release
of the newest keeps a project supported.

This guide is part of each release. An update replaces it with the guide of
the new release, so the guide in your project always describes the kit you
have installed. Edits you make to it are merged like edits to any kit file,
but a project's own notes belong in `project.json` or its own
documentation instead.

## Moving to 1.2.0 from an earlier release

From 1.1.0, `python3 .engineering-kit/kit/tools/kit.py update --apply` is
enough. From 1.0.1, 1.0.0 or a pilot release, name the version once:
`python3 .engineering-kit/kit/tools/kit.py update 1.2.0 --apply`. Nothing
else is required. To get the short command and the skills, add these to
`integrations` in `project.json` and update again:

```json
"launcher": {"grant": ["writes-launcher"]},
"agent-skills": {"grant": ["writes-skills"]}
```

The marked block in your instruction files gains one sentence pointing at
this guide; your text outside the block is unchanged.

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
  --rights "Our own work" --owner "Dana Ruiz"
```

The kit's maintainer applies the patch in the kit's repository, reviews it
like any change and releases it. Material from an employer, client or third
party stays out unless its owner cleared it.

## Decisions worth recording

Record a decision in the task, or in your project's own decision log, when
it is hard to reverse, surprising to a newcomer, and a real trade-off. Most
choices are none of these and need no record beyond the task itself.
