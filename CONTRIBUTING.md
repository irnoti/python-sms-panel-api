# Contributing

Bug reports and pull requests are welcome. Please:

1. Open an issue first for anything larger than a bug fix.
2. Keep changes focused and add or update tests (they use a fake transport; no key or network needed).
3. Run the checks below before pushing; CI runs the same.
4. Add a line to `CHANGELOG.md` under *Unreleased*.

## Releasing (maintainers)

1. Move *Unreleased* in `CHANGELOG.md` under the new version and bump the version where the package declares one.
2. Merge to `main`, then tag: `git tag vX.Y.Z && git push origin vX.Y.Z`.
3. The `release` workflow verifies the tag, tests, publishes and creates the GitHub release.
