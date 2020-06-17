import argparse
import logging
from types import SimpleNamespace

import pytest

import nutcli
from nutcli.commands import Actor, Command, CommandGroup, CommandParser, SubcommandsActor


def test_Actor__filter_parser_args__empty():
    actor = Actor()

    args = SimpleNamespace()
    assert not actor._filter_parser_args(args)

    args = SimpleNamespace(test=True)
    assert not actor._filter_parser_args(args)


def test_Actor__filter_parser_args__some():
    class TestActor(Actor):

        def __call__(self, arg1, arg2):
            pass

    actor = TestActor()

    args = SimpleNamespace()
    assert not actor._filter_parser_args(args)

    args = SimpleNamespace(test=True)
    assert not actor._filter_parser_args(args)

    args = SimpleNamespace(arg1=True)
    kwargs = actor._filter_parser_args(args)
    assert 'arg1' in kwargs
    assert kwargs['arg1'] is True
    assert len(kwargs) == 1

    args = SimpleNamespace(arg1=True, arg2=False)
    kwargs = actor._filter_parser_args(args)
    assert 'arg1' in kwargs
    assert kwargs['arg1'] is True
    assert 'arg2' in kwargs
    assert kwargs['arg2'] is False
    assert len(kwargs) == 2

    args = SimpleNamespace(arg1=True, arg2=False, test=1)
    kwargs = actor._filter_parser_args(args)
    assert 'arg1' in kwargs
    assert kwargs['arg1'] is True
    assert 'arg2' in kwargs
    assert kwargs['arg2'] is False
    assert len(kwargs) == 2


def test_Actor__filter_parser_args__kwargs():
    class TestActor(Actor):

        def __call__(self, arg1, **kwargs):
            pass

    actor = TestActor()

    args = SimpleNamespace()
    assert not actor._filter_parser_args(args)

    args = SimpleNamespace(test=True)
    assert args.__dict__ == actor._filter_parser_args(args)

    args = SimpleNamespace(arg1=True)
    assert args.__dict__ == actor._filter_parser_args(args)

    args = SimpleNamespace(arg1=True, arg2=False)
    assert args.__dict__ == actor._filter_parser_args(args)

    args = SimpleNamespace(arg1=True, arg2=False, test=1)
    assert args.__dict__ == actor._filter_parser_args(args)


def test_Actor__messages(caplog):
    class TestActor(Actor):

        def __call__(self):
            pass

    actor = TestActor(logger=nutcli.message)

    with caplog.at_level(logging.DEBUG):
        actor.debug('TEST')
    assert 'DEBUG' in caplog.text
    assert 'TEST' in caplog.text
    caplog.clear()

    with caplog.at_level(logging.DEBUG):
        actor.info('TEST')
    assert 'INFO' in caplog.text
    assert 'TEST' in caplog.text
    caplog.clear()

    with caplog.at_level(logging.DEBUG):
        actor.warning('TEST')
    assert 'WARNING' in caplog.text
    assert 'TEST' in caplog.text
    caplog.clear()

    with caplog.at_level(logging.DEBUG):
        actor.error('TEST')
    assert 'ERROR' in caplog.text
    assert 'TEST' in caplog.text
    caplog.clear()

    with caplog.at_level(logging.DEBUG):
        actor.critical('TEST')
    assert 'CRITICAL' in caplog.text
    assert 'TEST' in caplog.text
    caplog.clear()


def test_SubcommandsActor():
    actor1 = Actor()

    class TestActor(SubcommandsActor):

        def get_commands(self):
            return [Command('test1', 'test command', actor1)]

    parser = argparse.ArgumentParser()
    tactor = TestActor()
    tactor.setup_parser(parser)

    parser.print_help()
    return

    (args, invalid) = parser.parse_known_args(['test1'])
    assert args.func == actor1
    assert not invalid

    with pytest.raises(SystemExit):
        (args, invalid) = parser.parse_known_args(['test2'])


def test_CommandParser__basic():
    parser = argparse.ArgumentParser()
    actor1 = Actor()

    CommandParser('Test Commands')([
        Command('test1', 'test command', actor1),
    ]).setup_parser(parser)

    (args, invalid) = parser.parse_known_args(['test1'])
    assert args.func == actor1
    assert not invalid

    with pytest.raises(SystemExit):
        (args, invalid) = parser.parse_known_args(['test2'])


def test_CommandParser__list():
    parser = argparse.ArgumentParser()
    actor1 = Actor()
    actor2 = Actor()

    CommandParser('Test Commands')([
        Command('test1', 'test command', actor1),
        Command('test2', 'test command', actor2),
    ]).setup_parser(parser)

    (args, invalid) = parser.parse_known_args(['test1'])
    assert args.func == actor1
    assert not invalid

    (args, invalid) = parser.parse_known_args(['test2'])
    assert args.func == actor2
    assert not invalid

    with pytest.raises(SystemExit):
        (args, invalid) = parser.parse_known_args(['test3'])


def test_CommandParser__nested():
    parser = argparse.ArgumentParser()
    actor1 = Actor()
    actor2 = Actor()

    CommandParser('Test Commands')([
        Command('test1', 'test command', actor1),
        Command('nested', 'test command', CommandParser()([
            Command('test2', 'test command', actor2),
        ])),
    ]).setup_parser(parser)

    (args, invalid) = parser.parse_known_args(['test1'])
    assert args.func == actor1
    assert not invalid

    with pytest.raises(SystemExit):
        (args, invalid) = parser.parse_known_args(['test2'])

    (args, invalid) = parser.parse_known_args(['nested', 'test2'])
    assert args.func == actor2
    assert not invalid


def test_CommandGroup__basic():
    parser = argparse.ArgumentParser()
    actor1 = Actor()

    CommandParser('Test Commands')([
        CommandGroup('Test Group')([
            Command('test1', 'test command', actor1)
        ])
    ]).setup_parser(parser)

    (args, invalid) = parser.parse_known_args(['test1'])
    assert args.func == actor1
    assert not invalid

    with pytest.raises(SystemExit):
        (args, invalid) = parser.parse_known_args(['test2'])


def test_CommandGroup__list():
    parser = argparse.ArgumentParser()
    actor1 = Actor()
    actor2 = Actor()

    CommandParser('Test Commands')([
        CommandGroup('Test Group')([
            Command('test1', 'test command', actor1),
            Command('test2', 'test command', actor2),
        ])
    ]).setup_parser(parser)

    (args, invalid) = parser.parse_known_args(['test1'])
    assert args.func == actor1
    assert not invalid

    (args, invalid) = parser.parse_known_args(['test2'])
    assert args.func == actor2
    assert not invalid

    with pytest.raises(SystemExit):
        (args, invalid) = parser.parse_known_args(['test3'])


def test_CommandGroup__multiple():
    parser = argparse.ArgumentParser()
    actor1 = Actor()
    actor2 = Actor()
    actor3 = Actor()

    CommandParser('Test Commands')([
        CommandGroup('Test Group 1')([
            Command('test1', 'test command', actor1),
        ]),
        CommandGroup('Test Group 2')([
            Command('test2', 'test command', actor2),
        ]),
        Command('test3', 'test command', actor3),
    ]).setup_parser(parser)

    (args, invalid) = parser.parse_known_args(['test1'])
    assert args.func == actor1
    assert not invalid

    (args, invalid) = parser.parse_known_args(['test2'])
    assert args.func == actor2
    assert not invalid

    (args, invalid) = parser.parse_known_args(['test3'])
    assert args.func == actor3
    assert not invalid

    with pytest.raises(SystemExit):
        (args, invalid) = parser.parse_known_args(['test4'])
