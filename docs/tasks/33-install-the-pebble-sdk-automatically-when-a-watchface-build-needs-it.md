# Install the Pebble SDK when a build needs it

The watchface build should work after the SDK has been removed from Tinni, freeing its disk until another build needs the SDK. Add a simple automatic installation of the required Pebble SDK when absent, then remove the installed SDK from agent@tinni after the automatic reinstall has been verified. Preserve emulator state, settings and unrelated data.

On 2026-11-13, Pebble tool 5.0.40 installed SDK 4.17 twice into isolated homes. The first returned success despite an npm configuration error. The second used npm_config_userconfig=/dev/null and successfully built a copied watchface under nix-shell. Verify a missing-SDK build actually reinstalls and builds, handles failures visibly, and preserves existing builds. Check which exact SDK files and links are removed and report actual disk space recovered. Network access and license terms may be required.

## Result

**Who is affected:** Antti and agents who build the watch face on agent@tinni.
**The problem:** the Pebble SDK took about 780 MB on a nearly full disk, but
removing it would break `make build`. Without an SDK, pebble-tool itself would
install the unpinned latest SDK, and its npm step could fail while still
reporting success. **What changed:** [the watchface build recipe] now installs
the CI's SDK version (4.33.1, overridable with `PEBBLE_SDK_VERSION`) before
`make build` or `make clean` whenever no SDK is active, with the user's npm
configuration ignored. A failed installation stops make with an error before
anything is cleaned or built. **What is different:** the SDK has been removed
from agent@tinni, and the next watch-face build there reinstalls it.

Decision: the default is the CI version 4.33.1, not the 4.17 that agent@tinni had,
so local builds match release builds. The emulator storage for 4.17 is kept; it
is used again only if SDK 4.17 is reinstalled (`pebble sdk install 4.17`).

## Verification on agent@tinni, 2026-11-13

1. Inventory before removal of `~/.local/share/pebble-sdk/SDKs/4.17`: 31,491
   files, 37 symlinks, 3,214 directories, 701,614,268 bytes apparent size,
   779 MiB on disk. One link pointed outside the SDK:
   `.venv/bin/python3.13 -> /etc/profiles/per-user/agent/bin/python3.13`.
   The `SDKs/current` link pointed to `SDKs/4.17`.
2. Removed exactly `SDKs/4.17` and the `SDKs/current` link. Free space on `/`
   went from 6,703,656,960 to 7,520,100,352 bytes: 816,443,392 bytes recovered.
3. `make clean build` in the worktree with the real home and no SDK printed
   `No active Pebble SDK found; installing SDK 4.33.1.`, the terms and license
   notice, downloaded and installed the SDK, its Python and JS dependencies and
   toolchain, then cleaned and built `build/watchface.pbw` (exit 0, 23 s). The
   bundle's `appinfo.json` had version 0.3.0, the face UUID and `emery`. The npm
   step printed no errors; `node_modules` had 204 packages.
4. Rerunning `make build` with the SDK present did not install again (exit 0).
5. With the SDK moved away, `make clean build PEBBLE_SDK_VERSION=0.0.0` failed
   with exit 2 and `Pebble SDK 0.0.0 installation failed; nothing was built or
   cleaned.`; the previous bundle's SHA-256 was unchanged.
6. Removed the reinstalled SDK 4.33.1 (707,098,625 bytes apparent size). Final
   free space: 7,486,808,064 bytes, 783,151,104 bytes more than before step 2
   (other processes also write to the disk). `SDKs/` is now empty.
7. Preserved and checked: `4.17/emery/` emulator storage (flash image SHA-256
   unchanged), `settings.json` and `client_id` (SHA-256 unchanged),
   `oauth_firebase/`. pebble-tool rewrote `settings.json` and
   `pending_analytics.json` with identical content (new modification times).
   The shared checkout's `watchface/build/` was not touched.
8. Acceptance checks in temporary homes (also recorded in the receipt):
   `missing-sdk-install-build` installs and builds from nothing (exit 0, 19 s);
   `failed-install-preserves-bundle` fails the install, keeps a placeholder
   bundle and leaves no `SDKs/current` link (exit 0).

Limits: pebble-tool points `/var/tmp/pebble-sdk` at whichever home ran it last;
after the temporary-home checks it dangles until the next real build, as it did
before this task. The silent npm failure seen on 2026-11-13 was not reproduced;
it is avoided by `npm_config_userconfig=/dev/null`, not detected.

<details><summary>Guarded heavy commands</summary>

| Command | Outcome | Admission MemAvailable | Final MemAvailable | Start swap used | Swap growth | Elapsed | Status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `make clean build` with missing SDK (real home) | started at once, no wait | 43,438,816 kB | 44,036,856 kB | 10,123,216 kB | 93,184 kB | 23 s | exit 0 |
| isolated-home acceptance checks 1 and 2 | started at once, no wait | 44,180,680 kB | 44,392,724 kB | not recorded | not recorded | 19 s + under 5 s | exit 0, exit 0 |

</details>

[the watchface build recipe]: ../../watchface/Makefile?f
