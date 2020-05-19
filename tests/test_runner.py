import argparse
import logging

from nutcli.commands import Actor, Command, CommandParser
from nutcli.exceptions import TimeoutError
from nutcli.runner import Runner
from nutcli.shell import Shell


def test_Runner__Exception():
    class TestActor(Actor):

        def __call__(self):
            raise Exception()

    parser = argparse.ArgumentParser()
    CommandParser()([
        Command('test', '', TestActor()),
    ]).setup_parser(parser)

    runner = Runner('test', parser)
    rc = runner.execute(runner.parse_args(['test']))
    assert rc == 1


def test_Runner__ShellCommandError():
    class TestActor(Actor):

        def __call__(self):
            self.shell('exit 33')

    parser = argparse.ArgumentParser()
    CommandParser()([
        Command('test', '', TestActor()),
    ]).setup_parser(parser)

    runner = Runner('test', parser)
    rc = runner.execute(runner.parse_args(['test']))
    assert rc == 33


def test_Runner__ShellTimeoutError():
    class TestActor(Actor):

        def __call__(self):
            self.shell('sleep 2', timeout=1)

    parser = argparse.ArgumentParser()
    CommandParser()([
        Command('test', '', TestActor()),
    ]).setup_parser(parser)

    runner = Runner('test', parser, timeout_exit_code=255)
    rc = runner.execute(runner.parse_args(['test']))
    assert rc == 255


def test_Runner__TimeoutError():
    class TestActor(Actor):

        def __call__(self):
            raise TimeoutError(2, 'Timed out')

    parser = argparse.ArgumentParser()
    CommandParser()([
        Command('test', '', TestActor()),
    ]).setup_parser(parser)

    runner = Runner('test', parser, timeout_exit_code=255)
    rc = runner.execute(runner.parse_args(['test']))
    assert rc == 255


def test_Runner__actor_return_code():
    class TestActor(Actor):

        def __call__(self):
            return 5

    parser = argparse.ArgumentParser()
    CommandParser()([
        Command('test', '', TestActor()),
    ]).setup_parser(parser)

    runner = Runner('test', parser)
    rc = runner.execute(runner.parse_args(['test']))
    assert rc == 5


def test_Runner__shell_override():
    class TestActor(Actor):

        def __call__(self):
            result = self.shell('echo $TEST_VAR', capture_output=True)
            assert result.stdout == 'TEST'

    parser = argparse.ArgumentParser()
    CommandParser()([
        Command('test', '', TestActor()),
    ]).setup_parser(parser)

    runner = Runner('test', parser)
    runner.execute(
        runner.parse_args(['test']),
        shell=Shell(env={'TEST_VAR': 'TEST'})
    )


def test_Runner__args():
    class TestActor(Actor):

        def setup_parser(self, parser):
            parser.add_argument('--hello', action='store', type=str)

        def __call__(self, hello):
            assert self.cli_args is not None
            assert self.cli_args.hello == 'world'
            assert hello == 'world'

    parser = argparse.ArgumentParser()
    CommandParser()([
        Command('test', '', TestActor()),
    ]).setup_parser(parser)

    runner = Runner('test', parser)
    runner.execute(runner.parse_args(['test', '--hello', 'world']))


def test_Runner__cli_args():
    class TestActor(Actor):

        def __call__(self):
            assert self.cli_args is not None
            assert self.cli_args.hello == 'world'

    parser = argparse.ArgumentParser()
    parser.add_argument('--hello', action='store', type=str)
    CommandParser()([
        Command('test', '', TestActor()),
    ]).setup_parser(parser)

    runner = Runner('test', parser)
    runner.execute(runner.parse_args(['--hello', 'world', 'test']))


def test_Runner__logger_default(caplog):
    class TestActor(Actor):

        def __call__(self):
            self.info('TEST')

    parser = argparse.ArgumentParser()
    CommandParser()([
        Command('test', '', TestActor()),
    ]).setup_parser(parser)

    with caplog.at_level(logging.DEBUG):
        runner = Runner('test', parser)
        runner.default_logger().execute(runner.parse_args(['test']))

    assert caplog.records[0].name == 'nutcli.messages'
    assert caplog.records[0].message == 'TEST'


def test_Runner__logger_override(caplog):
    class TestActor(Actor):

        def __call__(self):
            self.info('TEST')

    parser = argparse.ArgumentParser()
    CommandParser()([
        Command('test', '', TestActor()),
    ]).setup_parser(parser)

    with caplog.at_level(logging.DEBUG):
        Runner('test', parser, logger=logging.getLogger('test')).execute(
            ['test']
        )
        runner = Runner('test', parser, logger=logging.getLogger('test'))
        rc = runner.default_logger().execute(runner.parse_args(['test']))

    assert caplog.records[0].name == 'test'
    assert caplog.records[0].message == 'TEST'
