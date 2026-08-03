import contextlib
import pytest
import threading

from unittest.mock import patch

from siliconcompiler.package import PathCache
from siliconcompiler.utils.multiprocessing import MPManager


@contextlib.contextmanager
def patch_sleep():
    """Records sleep durations instead of waiting."""
    sleeps = []
    with patch("siliconcompiler.package.cache.time.sleep", side_effect=sleeps.append):
        yield sleeps


@contextlib.contextmanager
def patch_nominal_jitter():
    """Pins the randomized delay to the midpoint of its jitter band."""
    with patch("siliconcompiler.package.cache.random.uniform",
               side_effect=lambda low, high: (low + high) / 2):
        yield


def test_init_defaults():
    cache = PathCache()

    assert cache.max_attempts == PathCache.DEFAULT_MAX_ATTEMPTS
    assert cache.max_attempts == 3
    assert cache.retry_delay == PathCache.DEFAULT_RETRY_DELAY
    assert cache.retry_backoff == PathCache.DEFAULT_RETRY_BACKOFF
    assert cache.get("missing") is None
    assert cache.attempts("missing") == 0
    assert cache.failure("missing") is None
    assert not cache.is_exhausted("missing")


def test_set_get():
    cache = PathCache()
    cache.set("id", "/some/path")

    assert cache.get("id") == "/some/path"


def test_set_stringifies(tmp_path):
    cache = PathCache()
    cache.set("id", tmp_path)

    assert cache.get("id") == str(tmp_path)
    assert isinstance(cache.get("id"), str)


def test_record_failure():
    cache = PathCache()

    assert cache.record_failure("id", ValueError("first")) == 1
    assert cache.attempts("id") == 1
    assert cache.failure("id") == "ValueError: first"
    assert not cache.is_exhausted("id")

    assert cache.record_failure("id", FileNotFoundError("second")) == 2
    assert cache.record_failure("id", FileNotFoundError("third")) == 3
    assert cache.attempts("id") == 3
    assert cache.failure("id") == "FileNotFoundError: third"
    assert cache.is_exhausted("id")


def test_record_failure_is_per_id():
    cache = PathCache()
    cache.record_failure("id0", ValueError("nope"))

    assert cache.attempts("id0") == 1
    assert cache.attempts("id1") == 0


def test_clear_failure():
    cache = PathCache()
    cache.record_failure("id", ValueError("nope"))
    cache.clear_failure("id")

    assert cache.attempts("id") == 0
    assert cache.failure("id") is None

    # Must not raise for an unknown id
    cache.clear_failure("other")


def test_set_max_attempts():
    cache = PathCache()
    cache.set_max_attempts(1)

    assert cache.max_attempts == 1
    assert not cache.is_exhausted("id")

    cache.record_failure("id", ValueError("nope"))
    assert cache.is_exhausted("id")


@pytest.mark.parametrize("value", (0, -1))
def test_set_max_attempts_invalid(value):
    with pytest.raises(ValueError, match="^max_attempts must be greater than 0$"):
        PathCache().set_max_attempts(value)


def test_set_retry_delay():
    cache = PathCache()
    cache.set_retry_delay(0)

    assert cache.retry_delay == 0


def test_set_retry_delay_invalid():
    with pytest.raises(ValueError, match="^retry_delay must not be negative$"):
        PathCache().set_retry_delay(-1)


def test_wait_before_retry_first_attempt():
    """A source that has not failed yet is never delayed."""
    cache = PathCache()
    cache.set_retry_delay(30)

    with patch_sleep() as sleeps:
        cache.wait_before_retry("id")

    assert sleeps == []


def test_wait_before_retry_backs_off():
    """Each delay grows by the backoff factor. Jitter is pinned to the nominal."""
    cache = PathCache()
    cache.set_retry_delay(2)
    cache.set_retry_backoff(2)

    seen = []
    for _ in range(3):
        cache.record_failure("id", ValueError("nope"))
        with patch_nominal_jitter(), patch_sleep() as sleeps:
            cache.wait_before_retry("id")
        seen.extend(sleeps)

    assert seen == [2, 4, 8]


def test_default_retry_ladder():
    """The shipped defaults give roughly 2s, 5s, 10s."""
    cache = PathCache()

    ladder = []
    for _ in range(3):
        cache.record_failure("id", ValueError("nope"))
        with patch_nominal_jitter():
            ladder.append(round(cache.next_retry_delay("id"), 1))

    assert ladder == [2.0, 4.5, 10.1]


def test_next_retry_delay_is_randomized():
    """
    Workers that failed together must not retry in unison, so the delay is
    jittered either side of its nominal value.
    """
    cache = PathCache()
    cache.set_retry_delay(10)
    cache.record_failure("id", ValueError("nope"))

    delays = {cache.next_retry_delay("id") for _ in range(50)}

    # Actually varying, and inside the jitter band around the 10s nominal
    assert len(delays) > 1
    jitter = PathCache.RETRY_JITTER
    assert all(10 * (1 - jitter) <= delay <= 10 * (1 + jitter) for delay in delays)


def test_next_retry_delay_jitter_bounds():
    """The band is exactly +/- RETRY_JITTER of nominal, at both extremes."""
    cache = PathCache()
    cache.set_retry_delay(8)
    cache.set_retry_backoff(1)
    cache.record_failure("id", ValueError("nope"))

    with patch("siliconcompiler.package.cache.random.uniform",
               side_effect=lambda low, high: low):
        assert cache.next_retry_delay("id") == 8 * (1 - PathCache.RETRY_JITTER)

    with patch("siliconcompiler.package.cache.random.uniform",
               side_effect=lambda low, high: high):
        assert cache.next_retry_delay("id") == 8 * (1 + PathCache.RETRY_JITTER)


def test_next_retry_delay_is_capped():
    """A large attempt budget must not turn the growth into an endless wait."""
    cache = PathCache()
    cache.set_max_attempts(50)
    cache.set_retry_delay(2)

    for _ in range(40):
        cache.record_failure("id", ValueError("nope"))

    # Jitter still applies at the ceiling, so the delay sits in the band below it
    delay = cache.next_retry_delay("id")
    assert PathCache.RETRY_MAX_DELAY * (1 - PathCache.RETRY_JITTER) <= delay
    assert delay <= PathCache.RETRY_MAX_DELAY


def test_next_retry_delay_at_ceiling_is_still_jittered():
    """Workers that all reached the cap must not resume in lockstep."""
    cache = PathCache()
    cache.set_max_attempts(50)
    cache.set_retry_delay(2)
    for _ in range(40):
        cache.record_failure("id", ValueError("nope"))

    assert len({cache.next_retry_delay("id") for _ in range(50)}) > 1


@pytest.mark.parametrize("attempts", (10 ** 3, 10 ** 6, 10 ** 9))
def test_next_retry_delay_survives_huge_attempt_counts(attempts):
    """
    The exponential is capped before it is raised to a power. Left unguarded it
    exceeds the float range and raises OverflowError from inside path resolution.
    """
    cache = PathCache()
    cache.set_max_attempts(10 ** 12)
    cache.seed({"failures": {"id": [attempts, "msg"]}})

    delay = cache.next_retry_delay("id")

    assert delay <= PathCache.RETRY_MAX_DELAY
    assert delay > 0


def test_wait_before_retry_survives_huge_attempt_counts():
    cache = PathCache()
    cache.set_max_attempts(10 ** 12)
    cache.seed({"failures": {"id": [10 ** 9, "msg"]}})

    with patch_sleep() as sleeps:
        cache.wait_before_retry("id")

    assert len(sleeps) == 1
    assert sleeps[0] <= PathCache.RETRY_MAX_DELAY


def test_next_retry_delay_unknown_id():
    assert PathCache().next_retry_delay("never-seen") == 0.0


def test_next_retry_delay_zero_base():
    cache = PathCache()
    cache.set_retry_delay(0)
    cache.record_failure("id", ValueError("nope"))

    assert cache.next_retry_delay("id") == 0.0


def test_set_retry_backoff():
    cache = PathCache()
    cache.set_retry_backoff(3)

    assert cache.retry_backoff == 3


def test_set_retry_backoff_of_one_is_constant():
    cache = PathCache()
    cache.set_retry_delay(5)
    cache.set_retry_backoff(1)

    ladder = []
    for _ in range(3):
        cache.record_failure("id", ValueError("nope"))
        with patch_nominal_jitter():
            ladder.append(cache.next_retry_delay("id"))

    assert ladder == [5, 5, 5]


def test_wait_before_retry_zero_delay():
    cache = PathCache()
    cache.set_retry_delay(0)
    cache.record_failure("id", ValueError("nope"))

    with patch_sleep() as sleeps:
        cache.wait_before_retry("id")

    assert sleeps == []


def test_export():
    cache = PathCache()
    cache.set("id0", "/path0")
    cache.record_failure("id1", ValueError("nope"))

    assert cache.export() == {
        "paths": {"id0": "/path0"},
        "failures": {"id1": [1, "ValueError: nope"]}
    }


def test_export_is_a_copy():
    cache = PathCache()
    cache.set("id0", "/path0")

    export = cache.export()
    export["paths"]["id0"] = "/tampered"

    assert cache.get("id0") == "/path0"


def test_seed_roundtrip():
    source = PathCache()
    source.set("id0", "/path0")
    source.record_failure("id1", ValueError("nope"))

    dest = PathCache()
    dest.seed(source.export())

    assert dest.get("id0") == "/path0"
    assert dest.attempts("id1") == 1
    assert dest.failure("id1") == "ValueError: nope"


def test_seed_ignore_failures():
    source = PathCache()
    source.set("id0", "/path0")
    source.record_failure("id1", ValueError("nope"))

    dest = PathCache()
    dest.seed(source.export(), include_failures=False)

    assert dest.get("id0") == "/path0"
    assert dest.attempts("id1") == 0
    assert dest.failure("id1") is None


def test_seed_keeps_highest_attempt_count():
    source = PathCache()
    source.record_failure("id", ValueError("one"))

    dest = PathCache()
    dest.record_failure("id", ValueError("a"))
    dest.record_failure("id", ValueError("b"))

    # Merging may only ever tighten the remaining budget
    dest.seed(source.export())
    assert dest.attempts("id") == 2
    assert dest.failure("id") == "ValueError: b"

    source.record_failure("id", ValueError("two"))
    source.record_failure("id", ValueError("three"))
    dest.seed(source.export())
    assert dest.attempts("id") == 3
    assert dest.failure("id") == "ValueError: three"


@pytest.mark.parametrize("payload", (None, "notadict", 5, [], {"paths": "notadict"},
                                     {"failures": "notadict"}, {}))
def test_seed_tolerates_junk(payload):
    cache = PathCache()
    cache.set("id", "/path")

    cache.seed(payload)

    assert cache.get("id") == "/path"


def test_seed_tolerates_malformed_failures():
    cache = PathCache()
    cache.seed({"failures": {"id0": "nottuple", "id1": [2, "ValueError: nope"]}})

    assert cache.attempts("id0") == 0
    assert cache.attempts("id1") == 2


def test_clear():
    cache = PathCache()
    cache.set("id0", "/path0")
    cache.record_failure("id1", ValueError("nope"))

    cache.clear()

    assert cache.get("id0") is None
    assert cache.attempts("id1") == 0


def test_clear_keeps_policy():
    cache = PathCache()
    cache.set_max_attempts(7)
    cache.set_retry_delay(0)
    cache.set_retry_backoff(4)

    cache.clear()

    assert cache.max_attempts == 7
    assert cache.retry_delay == 0
    assert cache.retry_backoff == 4


def test_thread_lock_is_stable():
    cache = PathCache()

    assert cache.thread_lock("id") is cache.thread_lock("id")


def test_thread_lock_is_per_id():
    cache = PathCache()

    assert cache.thread_lock("id0") is not cache.thread_lock("id1")


# ============================================================================
# Ownership
# ============================================================================

def test_repr():
    cache = PathCache()
    cache.set("id0", "/path")
    cache.record_failure("id1", ValueError("nope"))

    assert repr(cache) == "PathCache(paths=1, failures=1, max_attempts=3)"


def test_mpmanager_owns_one_cache():
    cache = MPManager.get_path_cache()

    assert isinstance(cache, PathCache)
    assert MPManager.get_path_cache() is cache


def test_cache_is_discarded_with_mpmanager():
    """The cache belongs to the process, so it dies with the manager."""
    cache = MPManager.get_path_cache()
    cache.set("id", "/path")

    MPManager.stop()

    assert MPManager.get_path_cache() is not cache
    assert MPManager.get_path_cache().get("id") is None


def test_cache_is_shared_across_schemas():
    """
    Cache IDs are content hashes, so one cache serves every schema in the process:
    the same source at the same reference always resolves to the same path.
    """
    from siliconcompiler import Design, Project

    project = Project("testproj")
    design = Design("testdesign")

    MPManager.get_path_cache().set("id", "/path")

    from siliconcompiler.package import Resolver
    assert Resolver("n", project, "source://x").cache.get("id") == "/path"
    assert Resolver("n", design, "source://x").cache.get("id") == "/path"
    assert Resolver("n", None, "source://x").cache.get("id") == "/path"


def test_cache_is_reachable_before_any_project_exists():
    """A resolver with no schema context must still find the cache."""
    from siliconcompiler.package import Resolver

    assert Resolver("n", None, "source://x").cache is MPManager.get_path_cache()


# ============================================================================
# Poor inputs
# ============================================================================

@pytest.mark.parametrize("value", ("notanumber", None, [], {}, object()))
def test_set_max_attempts_not_a_number(value):
    cache = PathCache()

    with pytest.raises((TypeError, ValueError), match="^max_attempts must be an integer"):
        cache.set_max_attempts(value)

    # Rejected input must leave the policy untouched
    assert cache.max_attempts == PathCache.DEFAULT_MAX_ATTEMPTS


def test_set_max_attempts_truncates_float():
    cache = PathCache()
    cache.set_max_attempts(2.9)

    assert cache.max_attempts == 2


def test_set_max_attempts_rejects_bool_false():
    with pytest.raises(ValueError, match="^max_attempts must be greater than 0$"):
        PathCache().set_max_attempts(False)


@pytest.mark.parametrize("value", ("notanumber", None, [], {}, object()))
def test_set_retry_delay_not_a_number(value):
    cache = PathCache()

    with pytest.raises((TypeError, ValueError), match="^retry_delay must be a number"):
        cache.set_retry_delay(value)

    assert cache.retry_delay == PathCache.DEFAULT_RETRY_DELAY


@pytest.mark.parametrize("value", (float("nan"), float("inf"), float("-inf")))
def test_set_retry_delay_rejects_non_finite(value):
    """nan and inf slip past a plain "< 0" test and would break time.sleep()."""
    cache = PathCache()

    with pytest.raises(ValueError, match="^retry_delay must be finite$"):
        cache.set_retry_delay(value)

    assert cache.retry_delay == PathCache.DEFAULT_RETRY_DELAY


@pytest.mark.parametrize("value", ("notanumber", None, [], {}, object()))
def test_set_retry_backoff_not_a_number(value):
    cache = PathCache()

    with pytest.raises((TypeError, ValueError), match="^retry_backoff must be a number"):
        cache.set_retry_backoff(value)

    assert cache.retry_backoff == PathCache.DEFAULT_RETRY_BACKOFF


@pytest.mark.parametrize("value", (float("nan"), float("inf"), float("-inf")))
def test_set_retry_backoff_rejects_non_finite(value):
    """inf would make the very first retry wait forever."""
    cache = PathCache()

    with pytest.raises(ValueError, match="^retry_backoff must be finite$"):
        cache.set_retry_backoff(value)

    assert cache.retry_backoff == PathCache.DEFAULT_RETRY_BACKOFF


@pytest.mark.parametrize("value", (0, 0.5, -1))
def test_set_retry_backoff_rejects_shrinking(value):
    """A factor below 1 would shrink each delay, which is backwards."""
    cache = PathCache()

    with pytest.raises(ValueError, match="^retry_backoff must be at least 1$"):
        cache.set_retry_backoff(value)

    assert cache.retry_backoff == PathCache.DEFAULT_RETRY_BACKOFF


def test_huge_backoff_is_still_capped():
    """Even an absurd factor cannot produce an unbounded wait."""
    cache = PathCache()
    cache.set_retry_backoff(10 ** 6)
    cache.record_failure("id", ValueError("nope"))
    cache.record_failure("id", ValueError("nope"))

    delay = cache.next_retry_delay("id")
    assert PathCache.RETRY_MAX_DELAY * (1 - PathCache.RETRY_JITTER) <= delay
    assert delay <= PathCache.RETRY_MAX_DELAY


def test_huge_backoff_with_huge_attempts_does_not_overflow():
    cache = PathCache()
    cache.set_max_attempts(10 ** 6)
    cache.set_retry_backoff(10 ** 6)
    cache.seed({"failures": {"id": [10 ** 5, "msg"]}})

    assert cache.next_retry_delay("id") <= PathCache.RETRY_MAX_DELAY


@pytest.mark.parametrize("cache_id", (None, 5, (), True))
def test_hashable_but_odd_cache_ids(cache_id):
    """Odd but hashable keys are stored without complaint or collision."""
    cache = PathCache()
    cache.set(cache_id, "/path")
    cache.record_failure(cache_id, ValueError("nope"))

    assert cache.get(cache_id) == "/path"
    assert cache.attempts(cache_id) == 1
    assert cache.get("other") is None


@pytest.mark.parametrize("cache_id", ([], {}, set()))
def test_unhashable_cache_ids(cache_id):
    """An unhashable key raises where a key must be resolved."""
    cache = PathCache()

    for call in (lambda: cache.get(cache_id),
                 lambda: cache.set(cache_id, "/path"),
                 lambda: cache.attempts(cache_id),
                 lambda: cache.failure(cache_id),
                 lambda: cache.is_exhausted(cache_id),
                 lambda: cache.record_failure(cache_id, ValueError("nope")),
                 lambda: cache.thread_lock(cache_id)):
        with pytest.raises(TypeError):
            call()


@pytest.mark.parametrize("cache_id", ([], {}, set()))
def test_unhashable_cache_id_leaves_cache_usable(cache_id):
    """
    Whether an unhashable key raises or is quietly ignored, it must never leave
    the cache damaged or holding its internal lock.
    """
    cache = PathCache()
    cache.set("good", "/path")

    # clear_failure is a no-op rather than an error while nothing has failed:
    # dict.pop with a default skips hashing on an empty dict.
    cache.clear_failure(cache_id)

    cache.record_failure("good", ValueError("nope"))
    with pytest.raises(TypeError):
        cache.clear_failure(cache_id)

    # Still fully usable, and the lock was released on every path
    assert cache.get("good") == "/path"
    cache.set("more", "/other")
    assert cache.export() == {
        "paths": {"good": "/path", "more": "/other"},
        "failures": {"good": [1, "ValueError: nope"]}
    }


def test_record_failure_with_odd_errors():
    """Errors carrying awkward messages must still be storable as text."""
    cache = PathCache()

    class Weird(Exception):
        def __str__(self):
            return "\x00binary\n\tmess"

    cache.record_failure("id", Weird())
    assert cache.failure("id") == "Weird: \x00binary\n\tmess"

    cache.record_failure("id2", ValueError())
    assert cache.failure("id2") == "ValueError: "


def test_set_with_none_path():
    """None is recorded as the string "None" rather than silently vanishing."""
    cache = PathCache()
    cache.set("id", None)

    assert cache.get("id") == "None"


@pytest.mark.parametrize("payload", (
    {"paths": {5: "/path"}},
    {"paths": {None: "/path"}},
    {"paths": {(): "/path"}},
))
def test_seed_skips_non_string_path_keys(payload):
    cache = PathCache()
    cache.seed(payload)

    assert cache.export()["paths"] == {}


def test_seed_skips_none_path_values():
    cache = PathCache()
    cache.seed({"paths": {"id0": None, "id1": "/path"}})

    assert cache.export()["paths"] == {"id1": "/path"}


def test_seed_coerces_path_values():
    cache = PathCache()
    cache.seed({"paths": {"id0": 5, "id1": ["a"]}})

    assert cache.get("id0") == "5"
    assert cache.get("id1") == "['a']"


@pytest.mark.parametrize("value", (
    "ab",             # a 2-char string would unpack into two characters
    [1],              # too short
    [1, "msg", 3],    # too long
    None,
    5,
    {"attempts": 1},
    [object(), "msg"],
    ["notanint", "msg"],
))
def test_seed_skips_malformed_failure_entries(value):
    cache = PathCache()
    cache.seed({"failures": {"id": value}})

    assert cache.attempts("id") == 0
    assert cache.failure("id") is None


def test_seed_skips_non_string_failure_keys():
    cache = PathCache()
    cache.seed({"failures": {5: [1, "msg"]}})

    assert cache.export()["failures"] == {}


def test_seed_clamps_negative_attempts():
    cache = PathCache()
    cache.seed({"failures": {"id": [-5, "msg"]}})

    assert cache.attempts("id") == 0
    assert not cache.is_exhausted("id")


def test_seed_coerces_failure_fields():
    cache = PathCache()
    cache.seed({"failures": {"id": ("2", 5)}})

    assert cache.attempts("id") == 2
    assert cache.failure("id") == "5"


def test_seed_huge_attempt_count_exhausts():
    cache = PathCache()
    cache.seed({"failures": {"id": [10 ** 9, "msg"]}})

    assert cache.is_exhausted("id")


def test_seed_partial_payload_keeps_valid_entries():
    """One bad entry must not discard the good ones alongside it."""
    cache = PathCache()
    cache.seed({
        "paths": {"good": "/path", 5: "/skipped"},
        "failures": {"good": [2, "msg"], "bad": "junk"}
    })

    assert cache.get("good") == "/path"
    assert cache.attempts("good") == 2
    assert cache.attempts("bad") == 0


def test_wait_before_retry_unknown_id():
    cache = PathCache()

    with patch_sleep() as sleeps:
        cache.wait_before_retry("never-seen")

    assert sleeps == []


def test_thread_safe_record_failure():
    cache = PathCache()
    cache.set_max_attempts(1000)

    def hammer():
        for _ in range(100):
            cache.record_failure("id", ValueError("nope"))

    threads = [threading.Thread(target=hammer) for _ in range(8)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert cache.attempts("id") == 800
