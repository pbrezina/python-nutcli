import argparse
import logging
import sys
import traceback

import colorama

import nutcli
from nutcli.commands import Actor
from nutcli.decorators import LogExecution, SideEffect
from nutcli.exceptions import TimeoutError
from nutcli.parser import NegateAction
from nutcli.shell import Shell, ShellCommandError, ShellError, ShellTimeoutError
from nutcli.utils import Colorize, check_instance


class Runner(object):
    """
    CLI Commands Runner.

    This is the main interface that takes care of processing arguments and
    executing requested commands.

    .. code-block:: python
        :caption: Example usage

        # Create argument parser.
        parser = argparse.ArgumentParser()

        # Create the runner object.
        runner = Runner('my-cli', parser).setup_parser()

        # Parse arguments - the runner internally process its own arguments
        # that were setup by previous call to `setup_parser()`.
        args = runner.parse_args(argv)

        # You can handle your own global arguments here.

        # Now we setup the default logger - it produces output to stdout
        # and stderr.
        runner.default_logger()

        # And finally, we execute the requested command and store its result
        # in `rc`.
        rc = runner.execute(args)
    """

    def __init__(
        self,
        name,
        parser,
        logger=None,
        timeout_exit_code=255
    ):
        """
        :param name: Runner name that will be visible in logs.
        :type name: str
        :param parser: Application ``argparse`` parser.
        :type parser: argparse.ArgumentParser
        :param logger: Logger to be used within the application,
            defaults to None (= :class:`nutcli.message`)
        :type logger: logger, optional
        :param timeout_exit_code: Return code in case of timeout error,
            defaults to 255
        :type timeout_exit_code: int, optional
        """

        self.name = name
        self.tag = name
        self.parser = parser
        self.logger = logger if logger is not None else nutcli.message
        self.timeout_exit_code = timeout_exit_code

    def setup_parser(self, options=None):
        """
        Setup nutcli default options.

        The options are:

            - ``--log-execution``: If set, calls decorated with
              :class:`nutcli.decorators.LogExecution` will be printed to the
              logger.
            - ``--dry-run``: If set, calls decorated with
              :class:`nutcli.decorators.SideEffect` will not be executed.,
            - ``--colors``, ``--no-colors``: Enable or disable colorized output.
              If not present, colors are enabled when stdout is a terminal.
            - ``--log-tag``, ``--no-log-tag``: Enable or disable message
              prefix when logging with default logger.

        .. note::
            You can override the option names by providing the options
            parameter. For example:

            .. code-block:: python

                options = {
                    'log-execution': 'log',
                    'dry-run': 'no-side-effects',
                    'colors': 'tty',
                    'log-tag': 'tag'
                }

        :param options: Override options names, defaults to None
        :type options: dict of str:str, optional
        :return: Self.
        :rtype: Runner
        """

        if options is None:
            options = {}

        if 'log-execution' not in options or options['log-execution'] is not None:
            self.parser.add_argument(
                '--' + options.get('log-execution', 'log-execution'),
                action='store_true', dest='_nutcli_log_execution',
                help='Log execution of operations that supports it.'
            )

        if 'dry-run' not in options or options['dry-run'] is not None:
            self.parser.add_argument(
                '--' + options.get('dry-run', 'dry-run'),
                action='store_true', dest='_nutcli_dry_run',
                help='Do not execute operations with side effects. '
                     'Only log what would be done.'
            )

        if 'colors' not in options or options['colors'] is not None:
            self.parser.add_argument(
                '--' + options.get('colors', 'colors'),
                '--no-' + options.get('colors', 'colors'),
                action=NegateAction, dest='_nutcli_colors',
                help='Enable/disable colorized output.'
            )

        if 'log-tag' not in options or options['log-tag'] is not None:
            self.parser.add_argument(
                '--' + options.get('log-tag', 'log-tag'),
                '--no-' + options.get('log-tag', 'log-tag'),
                action=NegateAction, dest='_nutcli_log_tag',
                help='Enable/disable message prefix.',
                default=True
            )

        return self

    def parse_args(self, argv):
        """
        Parse arguments and process internal ``nutcli`` arguments.

        :param argv: Command line arguments.
        :type argv: list of str
        :return: Parsed arguments in namespace.
        :rtype: argparse.Namespace
        """

        args = self.parser.parse_args(argv)

        if hasattr(args, '_nutcli_log_execution'):
            LogExecution.enabled(args._nutcli_log_execution)
            del args._nutcli_log_execution

        if hasattr(args, '_nutcli_dry_run'):
            SideEffect.dry_run(args._nutcli_dry_run)
            del args._nutcli_dry_run

        if hasattr(args, '_nutcli_colors'):
            if args._nutcli_colors is None:
                args._nutcli_colors = sys.stdout.isatty()
            Colorize.enabled(args._nutcli_colors)
            del args._nutcli_colors

        if hasattr(args, '_nutcli_log_tag'):
            if not args._nutcli_log_tag:
                self.tag = None
            del args._nutcli_log_tag

        return args

    def default_logger(self):
        """
        Setup default logger handlers.

        The ``DEBUG`` and ``INFO`` levels will be printed to ``stdout``.
        ``WARNING``, ``ERROR`` and ``CRITICAL`` are sent to ``stderr``.

        All messages are prefixed with ``[runner-name]`` string were the
        name is taken from the constructor.

        :return: Self.
        :rtype: Runner
        """

        class InfoFilter(logging.Filter):

            def filter(self, rec):
                return rec.levelno in (logging.DEBUG, logging.INFO)

        tag = f'[{self.tag}] ' if self.tag else ''

        stdout = logging.StreamHandler(sys.stdout)
        stdout.setLevel(logging.DEBUG)
        stdout.addFilter(InfoFilter())
        stdout.setFormatter(logging.Formatter(
            Colorize.all(tag, colorama.Fore.BLUE, colorama.Style.BRIGHT) + '%(message)s'
        ))

        stderr = logging.StreamHandler()
        stderr.setLevel(logging.WARNING)
        stderr.setFormatter(logging.Formatter(
            Colorize.all(tag, colorama.Fore.RED, colorama.Style.BRIGHT) + '%(message)s'
        ))

        self.logger.addHandler(stdout)
        self.logger.addHandler(stderr)
        self.logger.setLevel(logging.DEBUG)

        self.logger._log_prefix_len = len(tag)

        return self

    def execute(self, args, shell=None):
        """
        Process the arguments and either execute the command or print
        the usage message.

        :param args: Parsed arguments in namespace form.
        :type args: argparse.Namespace
        :param shell: Shell that will be used by actors, defaults to None
            (= ``Shell()``)
        :type shell: Shell, optional
        :return: Actor return code.
        :rtype: int
        """

        if not hasattr(args, 'func'):
            self.parser.print_help()
            return 0

        try:
            return self._call_actor(args.func, args, shell)
        except ShellError as e:
            for msg in e.pretty_message:
                self.logger.error(msg)
            traceback.print_exc()

            if isinstance(e, ShellCommandError):
                return e.rc

            if isinstance(e, ShellTimeoutError):
                return self.timeout_exit_code

            return 1
        except KeyboardInterrupt:
            self.logger.error('Program interupted by user.')
            return 1
        except Exception as e:
            cls = Colorize.all(e.__class__.__name__, colorama.Style.BRIGHT, colorama.Fore.RED)
            self.logger.error(f'Exception {cls}: {str(e)}')
            traceback.print_exc()

            if isinstance(e, TimeoutError):
                return self.timeout_exit_code

            return 1

    def _call_actor(self, actor, args, shell):
        check_instance(actor, (Actor, argparse.ArgumentParser))

        # Handler is ArgumentParser, print help.
        if isinstance(actor, argparse.ArgumentParser):
            actor.print_help()
            return 1

        del args.func

        actor._setup_root_actor(
            cli_args=args,
            logger=self.logger,
            shell=shell if shell is not None else Shell()
        )

        return actor(**actor._filter_parser_args(args))
