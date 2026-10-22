Steward issue, 2026-10-22 05:11 refill. Goal: agentic-leverage (pebble-quota is tier 1 in `<steward-vault>/Goals.md`). Estimated 45 min. From F5 and draft D1 of [the 2026-10-22 docs review](../reviews/2026-10-22-docs-review.md).

Agents' automatic edit check runs Ruff and `ty` on every edit here, and both report the same findings on unchanged `main`: seven from Ruff and four from `ty` (optional timestamp and server typing, style and file-mode findings). Every worker therefore starts from red checks and has to tell old findings from new ones. The [README](../../README.md) documents only the unittest command.

## Work

1. On `main`, run `ruff check .` and `ty check`, and record the eleven findings in this task record.
2. Fix each one without changing behaviour. Keep each provider's failure isolated from the others. For a file-mode finding, set the executable bit or drop the shebang, whichever matches how the file is run.
3. If a finding is a false positive, silence it narrowly (one rule, one file) with a comment that says why; never disable a rule for the whole repository.
4. Add both commands to the README's "Tests and status" section, beside the unittest command.

Leave out CI integration: the proposal "Gate releases on collector and phone behavior checks" ([7]) owns it.

## Acceptance

- `ruff check .` and `ty check` exit 0; `python3 -m unittest discover -s tests -v` passes all 66 tests, unchanged.
- No change to what the collector reads, writes or serves.
- Handoff: a short outcome; details go in this task record.

Tracker: [the pebble-quota tracker](../../TASKS.md).

[7]: 7-gate-releases-on-collector-and-phone-behavior-checks.md

## Record

### Findings on `main`

Ruff 0.16.8 and ty 0.0.84, run from the repository root at `07c00fe` with no
project configuration (Ruff's default rule set). The "seven and four" above are
the findings in `collector/pebble_quota.py` alone. Over the whole tree, as the
acceptance commands run, `ruff check .` reported 26 findings and `ty check` 12;
all 38 are fixed.

`ruff check .`, 26 findings:

| File | Line | Rule | Fix |
| --- | --- | --- | --- |
| `collector/pebble_quota.py` | 1 | EXE001 shebang, not executable | Shebang dropped |
| `collector/pebble_quota.py` | 24 | UP035 `typing.Callable` | Import from `collections.abc` |
| `collector/pebble_quota.py` | 56 | PYI041 `int \| float` | `float` |
| `collector/pebble_quota.py` | 494 | BLE001 blind `except` | `noqa`: isolates providers |
| `collector/pebble_quota.py` | 518 | BLE001 blind `except` | `noqa`: temperature is best-effort |
| `collector/pebble_quota.py` | 622 | BLE001 blind `except` | `noqa`: refresh loop keeps serving |
| `collector/pebble_quota.py` | 691 | BLE001 blind `except` | `noqa`: unreadable snapshot is a 503 |
| `spikes/001-quota-collectors/probe.py` | 1 | EXE001 shebang, not executable | Shebang dropped |
| `spikes/001-quota-collectors/probe.py` | 18, 26 | PYI041 `int \| float` (×2) | `float` |
| `spikes/001-quota-collectors/probe.py` | 145 | BLE001 blind `except` | `noqa`: isolates providers |
| `tests/test_pebble_quota.py` | 1 | I001 unsorted imports | `ruff check --fix` |
| `tests/test_pebble_quota.py` | 188, 556, 571, 612, 675, 694, 1029 | SIM117 nested `with` (×7) | Combined into one `with` |
| `tests/test_pebble_quota.py` | 197, 436, 596, 875 | RUF012 mutable class attribute (×4) | `ClassVar[...]` annotation |
| `tests/test_pebble_quota.py` | 420 | PYI034 `__enter__` return type | `Self` |
| `tests/test_pebble_quota.py` | 420 | UP037 quoted annotation | Gone with `Self` |
| `tests/test_pebble_quota.py` | 949 | ISC004 implicit concatenation in list | Parenthesised |

`ty check`, 12 findings:

| File | Line | Rule | Fix |
| --- | --- | --- | --- |
| `collector/pebble_quota.py` | 604 | unsupported-operator, `int - (int \| None)` | Call `epoch(last_success)` once and test that value |
| `collector/pebble_quota.py` | 682, 683, 687 | unresolved-attribute, `BaseServer.token`/`.snapshot` (×3) | Annotate `Handler.server: QuotaServer`; dropped the mypy `type: ignore` comments |
| `tests/test_pebble_quota.py` | 527, 860, 969, 1008 | invalid-argument-type, `HTTPError` headers `{}` (×4) | Empty `Message()` |
| `tests/test_pebble_quota.py` | 722, 723 | unresolved-attribute, `Popen.stdin`/`.stdout` may be `None` (×2) | `assert` both pipes |
| `tests/test_pebble_quota.py` | 747, 748 | no-matching-overload and unsupported-operator, `shutil.which()` may be `None` | Resolve `make` and `bash` first, `assert` both |

### Decisions

- **Shebangs:** dropped rather than made executable. The README and the
  deployed systemd unit (`home-manager/features/agent-workloads.nix` in
  nixos-config) run the collector as `python3 collector/pebble_quota.py`; the
  prototype has no documented direct invocation.
- **BLE001:** the five broad handlers are deliberate isolation boundaries, so
  narrowing them would change behaviour, for example letting a `KeyError` from
  one provider's payload cost the other provider its quota. Each has a per-line
  `# noqa: BLE001` with its reason; no rule is disabled anywhere else.
- **Behaviour:** the collector changes are annotations, an import location and
  one local variable; `epoch()` is pure, so calling it once gives the same
  value. An empty `Message()` is falsy like `{}`, so the 429 `Retry-After` path
  the tests exercise is unchanged. Test assertions and the test count are
  unchanged.
- **Python version:** `typing.Self` needs Python 3.11, which the tests already
  required through `TestCase.enterContext`.
- **README:** "Tests and status" lists `ruff check .` and `ty check` beside the
  unittest command and says CI runs none of them; CI integration stays with [7].

### Verification

- `ruff check .` and `ty check` exit 0 on the branch.
- `python3 -m unittest discover -s tests -v`: 66 tests pass before and after,
  with identical test names.

### Guarded heavy commands

| Command | Outcome | Admission MemAvailable | Final MemAvailable | Swap at start | Swap growth | Elapsed | Status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `python3 -m unittest discover -s tests -v` (baseline) | Started at once, no wait | 2592 MiB | 2498 MiB | 2522 MiB | 3 MiB | 12 s | Exit 0 |
| `python3 -m unittest discover -s tests -v` (after fixes) | Started at once, no wait | 2686 MiB | 2534 MiB | 2523 MiB | 0 MiB | 10 s | Exit 0 |

`ruff check .` and `ty check` cover five Python files and finish in under a
second, so they ran unguarded.
