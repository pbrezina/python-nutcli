import logging
import time

import mock
import pytest

from nutcli.decorators import Identity, IgnoreErrors, LogExecution, SideEffect, Timeout
from nutcli.exceptions import TimeoutError
from nutcli.utils import LogExecutionPrinter


def test_Identity():
    def fn(arg):
        return arg

    assert Identity(fn)('hello') == fn('hello')


def test_IgnoreErrors():
    @IgnoreErrors
    def fn():
        raise Exception('hello world')

    assert fn() is None


def test_Timeout__none():
    @Timeout(None)
    def fn():
        return True

    assert fn()


def test_Timeout__no_message():
    @Timeout(1)
    def fn():
        time.sleep(2)

    with pytest.raises(TimeoutError) as e:
        assert fn()

    assert e.value.timeout == 1
    assert str(e.value) == 'Operation timed out.'


def test_Timeout__custom_message():
    @Timeout(1, 'TEST')
    def fn():
        time.sleep(2)

    with pytest.raises(TimeoutError) as e:
        assert Timeout(1, 'TEST')(fn)()

    assert e.value.timeout == 1
    assert str(e.value) == 'TEST'


@pytest.mark.parametrize('fmt, seconds', [
    ('1 second', 1),
    ('1 seconds', 1),
    ('0.017 minute', 1),
    ('0.017 minutes', 1),
    ('0.00028 hour', 1),
    ('0.00028 hours', 1),
    ('1 second 0.017 minutes 0 hours', 2),
])
def test_Timeout__format(fmt, seconds):
    @Timeout(fmt)
    def fn():
        time.sleep(3)

    with pytest.raises(TimeoutError) as e:
        assert Timeout(fmt)(fn)()

    assert e.value.timeout == seconds


@mock.patch(
    'nutcli.decorators.LogExecution.should_log_execution',
    new_callable=mock.PropertyMock,
    return_value=False
)
def test_LogExecution__disabled(_, caplog):
    @LogExecution()
    def fn():
        return True

    with caplog.at_level(logging.DEBUG):
        assert fn()

    assert not caplog.text


@mock.patch(
    'nutcli.decorators.LogExecution.should_log_execution',
    new_callable=mock.PropertyMock,
    return_value=True
)
def test_LogExecution__default_printer(_, caplog):
    @LogExecution()
    def fn():
        return True

    with caplog.at_level(logging.DEBUG):
        assert fn()

    assert 'test_LogExecution__default_printer.<locals>.fn()' in caplog.text


@mock.patch(
    'nutcli.decorators.LogExecution.should_log_execution',
    new_callable=mock.PropertyMock,
    return_value=True
)
def test_LogExecution__message(_, caplog):
    @LogExecution(message='TEST')
    def fn():
        return True

    with caplog.at_level(logging.DEBUG):
        assert fn()

    assert 'TEST' in caplog.text


@mock.patch(
    'nutcli.decorators.LogExecution.should_log_execution',
    new_callable=mock.PropertyMock,
    return_value=True
)
def test_LogExecution__custom_printer(_, caplog):
    class TestPrinter(LogExecutionPrinter):

        def __call__(self, message, function, args, kwargs):
            logging.info('TEST')

    @LogExecution(printer=TestPrinter())
    def fn():
        return True

    with caplog.at_level(logging.DEBUG):
        assert fn()

    assert 'TEST' in caplog.text


@mock.patch(
    'nutcli.decorators.SideEffect.is_dry_run',
    new_callable=mock.PropertyMock,
    return_value=False
)
def test_SideEffect__disabled(_, caplog):
    @SideEffect()
    def fn():
        logging.info('TEST')
        return True

    with caplog.at_level(logging.DEBUG):
        assert fn()

    assert 'TEST' in caplog.text


@mock.patch(
    'nutcli.decorators.SideEffect.is_dry_run',
    new_callable=mock.PropertyMock,
    return_value=True
)
def test_SideEffect__default_printer(_, caplog):
    @SideEffect()
    def fn():
        logging.info('TEST')
        return True

    with caplog.at_level(logging.DEBUG):
        assert fn() is None

    assert 'TEST' not in caplog.text
    assert 'test_SideEffect__default_printer.<locals>.fn()' in caplog.text


@mock.patch(
    'nutcli.decorators.SideEffect.is_dry_run',
    new_callable=mock.PropertyMock,
    return_value=True
)
def test_SideEffect__message(_, caplog):
    @SideEffect(message='HELLO')
    def fn():
        logging.info('TEST')
        return True

    with caplog.at_level(logging.DEBUG):
        assert fn() is None

    assert 'TEST' not in caplog.text
    assert 'HELLO' in caplog.text


@mock.patch(
    'nutcli.decorators.SideEffect.is_dry_run',
    new_callable=mock.PropertyMock,
    return_value=True
)
def test_SideEffect__custom_printer(_, caplog):
    class TestPrinter(LogExecutionPrinter):

        def __call__(self, message, function, args, kwargs):
            logging.info('HELLO')

    @SideEffect(printer=TestPrinter())
    def fn():
        logging.info('TEST')
        return True

    with caplog.at_level(logging.DEBUG):
        assert fn() is None

    assert 'TEST' not in caplog.text
    assert 'HELLO' in caplog.text


@mock.patch(
    'nutcli.decorators.SideEffect.is_dry_run',
    new_callable=mock.PropertyMock,
    return_value=True
)
def test_SideEffect__custom_return(_, caplog):
    @SideEffect(message='HELLO', returns='RETURN-VALUE')
    def fn():
        logging.info('TEST')
        return True

    with caplog.at_level(logging.DEBUG):
        assert fn() == 'RETURN-VALUE'

    assert 'TEST' not in caplog.text
    assert 'HELLO' in caplog.text
