import logging

import pytest

from siliconcompiler.utils.logging import SCSuppressLoggerFilter, SCTeeLoggerHandler


# ---------------------------------------------------------------------------
# SCSuppressLoggerFilter
# ---------------------------------------------------------------------------

def _make_record(level=logging.INFO, msg="hello"):
    return logging.LogRecord(
        name="test", level=level, pathname=__file__, lineno=1,
        msg=msg, args=None, exc_info=None)


def test_suppress_filter_inactive_passes_records():
    f = SCSuppressLoggerFilter()
    assert f.active is False
    assert f.filter(_make_record()) is True


def test_suppress_filter_active_blocks_records():
    f = SCSuppressLoggerFilter()
    f.active = True
    assert f.filter(_make_record()) is False


def test_suppress_filter_is_togglable():
    f = SCSuppressLoggerFilter()
    rec = _make_record()
    assert f.filter(rec) is True
    f.active = True
    assert f.filter(rec) is False
    f.active = False
    assert f.filter(rec) is True


def test_suppress_filter_attached_to_handler_blocks_emit():
    """Filter on a handler should prevent emission while active and resume
    emission once the filter is deactivated."""
    received = []

    class _Capture(logging.Handler):
        def emit(self, record):
            received.append(record.getMessage())

    handler = _Capture()
    filt = SCSuppressLoggerFilter()
    handler.addFilter(filt)

    logger = logging.getLogger("test_suppress_filter_attached_to_handler_blocks_emit")
    logger.handlers = []
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

    logger.info("first")
    filt.active = True
    logger.info("second")
    filt.active = False
    logger.info("third")

    assert received == ["first", "third"]


# ---------------------------------------------------------------------------
# SCTeeLoggerHandler
# ---------------------------------------------------------------------------

class _Capture(logging.Handler):
    def __init__(self):
        super().__init__()
        self.records = []

    def emit(self, record):
        self.records.append(record.getMessage())


@pytest.fixture
def logger():
    lg = logging.getLogger(f"test_tee_{id(object())}")
    lg.handlers = []
    lg.setLevel(logging.INFO)
    yield lg
    lg.handlers = []


def test_tee_forwards_to_all_logger_handlers(logger):
    a, b = _Capture(), _Capture()
    logger.addHandler(a)
    logger.addHandler(b)

    tee = SCTeeLoggerHandler(logger)
    tee.handle(_make_record(msg="forwarded"))

    assert a.records == ["forwarded"]
    assert b.records == ["forwarded"]


def test_tee_skips_specified_handler(logger):
    a, b = _Capture(), _Capture()
    logger.addHandler(a)
    logger.addHandler(b)

    tee = SCTeeLoggerHandler(logger, skip=a)
    tee.handle(_make_record(msg="forwarded"))

    assert a.records == []
    assert b.records == ["forwarded"]


def test_tee_resolves_handlers_dynamically(logger):
    """A handler added to the logger after the tee was constructed must
    still receive forwarded records — this is the whole point of using a
    tee rather than passing a static handler list to the QueueListener."""
    tee = SCTeeLoggerHandler(logger)

    a = _Capture()
    logger.addHandler(a)
    tee.handle(_make_record(msg="first"))

    b = _Capture()
    logger.addHandler(b)
    tee.handle(_make_record(msg="second"))

    assert a.records == ["first", "second"]
    assert b.records == ["second"]


def test_tee_picks_up_removed_handlers(logger):
    """Conversely, removing a handler from the logger must stop forwarding
    to it — the tee should not retain a stale reference."""
    a = _Capture()
    logger.addHandler(a)

    tee = SCTeeLoggerHandler(logger)
    tee.handle(_make_record(msg="before-remove"))
    logger.removeHandler(a)
    tee.handle(_make_record(msg="after-remove"))

    assert a.records == ["before-remove"]


def test_tee_tolerates_handler_emit_failure(logger):
    """A misbehaving downstream handler must not break delivery to the
    other handlers in the chain."""
    class _Boom(logging.Handler):
        def emit(self, record):
            raise RuntimeError("boom")

    good = _Capture()
    logger.addHandler(_Boom())
    logger.addHandler(good)

    tee = SCTeeLoggerHandler(logger)
    tee.handle(_make_record(msg="survive"))

    assert good.records == ["survive"]
