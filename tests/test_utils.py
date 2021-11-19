import logging

import pytest

from nutcli.utils import LogExecutionPrinter, get_as_list, dict_to_namespace


def test_get_as_list__list():
    result = get_as_list([])
    assert result == []

    result = get_as_list([1])
    assert result == [1]

    result = get_as_list([1, 'a'])
    assert result == [1, 'a']


def test_get_as_list__tuple():
    result = get_as_list(())
    assert result == []

    result = get_as_list((1))
    assert result == [1]

    result = get_as_list((1, 'a'))
    assert result == [1, 'a']


def test_get_as_list__None():
    result = get_as_list(None)
    assert result == []


def test_get_as_list__misc():
    result = get_as_list(1)
    assert result == [1]

    result = get_as_list('a')
    assert result == ['a']

    result = get_as_list({'a': 'b'})
    assert result == [{'a': 'b'}]


def test_dict_to_namespace():
    result = dict_to_namespace({'a': 1, 'b': 2})
    assert hasattr(result, 'a')
    assert hasattr(result, 'b')
    assert result.a == 1
    assert result.b == 2

    result = dict_to_namespace({'a': 1, 'b': {'c': 3}})
    assert hasattr(result, 'a')
    assert hasattr(result, 'b')
    assert hasattr(result.b, 'c')
    assert result.a == 1
    assert result.b.c == 3


def test_dict_to_namespace__error():
    with pytest.raises(ValueError):
        dict_to_namespace(None)

    with pytest.raises(ValueError):
        dict_to_namespace(1)


def test_LogExecutionPrinter__skip_self_false(caplog):
    printer = LogExecutionPrinter(False)

    def test_fn(*args, **kwargs):
        pass

    with caplog.at_level(logging.DEBUG):
        printer(None, test_fn, (), {})
    assert 'test_LogExecutionPrinter__skip_self_false.<locals>.test_fn()' in caplog.text
    caplog.clear()

    with caplog.at_level(logging.DEBUG):
        printer(None, test_fn, (1), {})
    assert 'test_LogExecutionPrinter__skip_self_false.<locals>.test_fn(1)' in caplog.text
    caplog.clear()

    with caplog.at_level(logging.DEBUG):
        printer(None, test_fn, (1, 'a'), {})
    assert "test_LogExecutionPrinter__skip_self_false.<locals>.test_fn(1, 'a')" in caplog.text
    caplog.clear()

    with caplog.at_level(logging.DEBUG):
        printer(None, test_fn, (1), {'test': 2})
    assert 'test_LogExecutionPrinter__skip_self_false.<locals>.test_fn(1, test=2)' in caplog.text
    caplog.clear()

    with caplog.at_level(logging.DEBUG):
        printer(None, test_fn, (1), {'test': 2, 'world': 3})
    assert 'test_LogExecutionPrinter__skip_self_false.<locals>.test_fn(1, test=2, world=3)' in caplog.text
    caplog.clear()


def test_LogExecutionPrinter__skip_self_true(caplog):
    printer = LogExecutionPrinter(True)

    def test_fn(self, *args, **kwargs):
        pass

    with caplog.at_level(logging.DEBUG):
        printer(None, test_fn, ('self'), {})
    assert 'test_LogExecutionPrinter__skip_self_true.<locals>.test_fn()' in caplog.text
    caplog.clear()

    with caplog.at_level(logging.DEBUG):
        printer(None, test_fn, ('self', 1), {})
    assert 'test_LogExecutionPrinter__skip_self_true.<locals>.test_fn(1)' in caplog.text
    caplog.clear()

    with caplog.at_level(logging.DEBUG):
        printer(None, test_fn, ('self', 1, 'a'), {})
    assert "test_LogExecutionPrinter__skip_self_true.<locals>.test_fn(1, 'a')" in caplog.text
    caplog.clear()

    with caplog.at_level(logging.DEBUG):
        printer(None, test_fn, ('self', 1), {'test': 2})
    assert 'test_LogExecutionPrinter__skip_self_true.<locals>.test_fn(1, test=2)' in caplog.text
    caplog.clear()

    with caplog.at_level(logging.DEBUG):
        printer(None, test_fn, ('self', 1), {'test': 2, 'world': 3})
    assert 'test_LogExecutionPrinter__skip_self_true.<locals>.test_fn(1, test=2, world=3)' in caplog.text
    caplog.clear()
