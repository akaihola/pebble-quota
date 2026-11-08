# Changelog

## [0.3.0](https://github.com/akaihola/pebble-quota/compare/v0.1.0...v0.3.0) (2026-11-08)


### Features

* carry freshness and failure status through to the watch ([20644d3](https://github.com/akaihola/pebble-quota/commit/20644d3b69324d699b930e84f8b0821904945e90))
* enforce the five-line collector, phone and watch contract ([c9de5a5](https://github.com/akaihola/pebble-quota/commit/c9de5a529f3f205c6a8ad4424a68756827f7000e))
* settings page for endpoint + token, survives reinstalls ([91a4ac9](https://github.com/akaihola/pebble-quota/commit/91a4ac94e4da4a12bd18570fd9624f8fbd0b93aa))


### Bug Fixes

* configurable capability, TASKS dedup, phone-side endpoint docs ([535ef7b](https://github.com/akaihola/pebble-quota/commit/535ef7bc7b000ad8b5bbeb917d8de4bb4f7e5f4b))
* **phone:** discard superseded quota responses and bound freshness guard ([e225b15](https://github.com/akaihola/pebble-quota/commit/e225b15301363c14bd05d5f0242925ebe1ccd00f))
* **security:** isolate collector and build secrets and back off startup failures ([5b7c714](https://github.com/akaihola/pebble-quota/commit/5b7c7147641001661efdda0fc9ca71c8e2cc0420))
* **watchface:** automate versioned releases ([cb47658](https://github.com/akaihola/pebble-quota/commit/cb47658b6c93fcd8dd6f2bee337e065e69a22d48))
* **watchface:** bundle the settings page so it opens when the collector moved ([4768514](https://github.com/akaihola/pebble-quota/commit/476851450f06a15f4c2f37f2d5afbb3ee42ff9cd))
* **watch:** reject zero-byte string tuples before replacing rows ([17031b0](https://github.com/akaihola/pebble-quota/commit/17031b0069cef67c469135f0cff48a864bf91ab1))
