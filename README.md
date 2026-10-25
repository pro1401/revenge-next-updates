# Personal Revenge Next update source

Unofficial distribution mirror of unchanged production builds from
[revenge-mod/revenge-bundle-next](https://github.com/revenge-mod/revenge-bundle-next).
Checks hourly for production artifacts from the official main branch, verifies
the archive against GitHub's SHA-256 digest, and publishes the bundle together
with its corresponding source and license. GitHub schedule execution can be delayed.

Loader URL: `https://raw.githubusercontent.com/pro1401/revenge-next-updates/main/revenge.bundle`

Manifest URL: `https://raw.githubusercontent.com/pro1401/revenge-next-updates/main/manifest.json`

Revenge downloads updates on application launch. Plugin updates use their own
repository settings. This does not update the Discord APK or its native loader.

The phone retains the last downloaded bundle for offline launches. This is an
experimental upstream branch; compatibility with future loader and Discord
versions is not guaranteed. GitHub can disable scheduled workflows after 60 days
of repository inactivity; check Actions if updates stop.

See `build-info.json` for provenance, `source.zip` for corresponding source,
and `LICENSE.upstream` for the upstream GPL-3.0 license.
