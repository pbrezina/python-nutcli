import argparse
import inspect

from nutcli.parser import SubparsersAction
from nutcli.utils import check_instance, get_as_list


class Actor(object):
    """
    The command actor. It defines the handler that is executed either via
    the command line or through other actors when re-using the code.

    .. code-block:: python
        :caption: Example usage

        class ExampleActor(Actor):
            def setup_parser(parser):
                parser.add_argument('--hello', action='store', type=str)

            def __call__(self, hello):
                self.info(hello)
    """

    def __init__(self, parent=None, cli_args=None, shell=None, logger=None):
        """
        :param parent: Parent actor to inherit settings from, defaults to None
        :type parent: Actor, optional
        :param cli_args: Override cli arguments, defaults to None
        :type cli_args: list of any, optional
        :param shell: Override shell, defaults to None
        :type shell: Shell, optional
        :param logger: Override logger, defaults to None
        :type logger: logger, optional

        :ivar cli_args: All arguments passed to the command line.
        :ivar shell: Instance of :class:`nutcli.shell.Shell` ready to be used
            in the actor.
        """
        self.cli_args = cli_args
        self.logger = logger
        self.shell = shell

        if parent is not None:
            self.cli_args = parent.cli_args if cli_args is None else cli_args
            self.logger = parent.logger if logger is None else logger
            self.shell = parent.shell.clone() if shell is None else shell

    def _setup_root_actor(self, cli_args, logger, shell):
        if self.cli_args is None:
            self.cli_args = cli_args

        if self.logger is None:
            self.logger = logger

        if self.shell is None:
            self.shell = shell

    def setup_parser(self, parser):
        """
        Setup argument parser.

        You should override this in your actor if it accepts any arguments.

        :param parser: You can add arguments to this parser.
        :type parser: argparse.Parser
        """
        pass

    def _filter_parser_args(self, args):
        spec = inspect.getfullargspec(self.__call__)
        if spec.varkw is None:
            kwargs = {}
            for arg in args.__dict__:
                if arg in spec.args:
                    kwargs[arg] = args.__dict__[arg]
        else:
            kwargs = {**args.__dict__}

        # Remove leading '--' from remaining arguments
        for value in kwargs.values():
            if type(value) is list:
                if value and value[0] == '--':
                    value.pop(0)

        return kwargs

    @property
    def _log_prefix_len(self):
        if hasattr(self.logger, '_log_prefix_len'):
            return self.logger._log_prefix_len

        return 0

    def debug(self, msg, *args, **kwargs):
        """
        Log a debug message.

        :param msg: The message.
        :type msg: str
        """

        self.logger.debug(msg, *args, **kwargs)

    def info(self, msg, *args, **kwargs):
        """
        Log an information message.

        :param msg: The message.
        :type msg: str
        """

        self.logger.info(msg, *args, **kwargs)

    def warning(self, msg, *args, **kwargs):
        """
        Log a warning message.

        :param msg: The message.
        :type msg: str
        """

        self.logger.warning(msg, *args, **kwargs)

    def error(self, msg, *args, **kwargs):
        """
        Log an error message.

        :param msg: The message.
        :type msg: str
        """

        self.logger.error(msg, *args, **kwargs)

    def critical(self, msg, *args, **kwargs):
        """
        Log a critical message.

        :param msg: The message.
        :type msg: str
        """

        self.logger.critical(msg, *args, **kwargs)

    def __call__(self):
        """
        Command handler.

        You should override this in your actor.

        :raises NotImplementedError: The error is risen if this method is not
            overridden.
        """
        raise NotImplementedError("Actor is not fully implemented.")


class SubcommandsActor(Actor):
    """
    This is a special actor that can provide additional subcommands.

    You can use this to reuse code for your cli when you want to use the same
    actors but need to instantiate them with different parameters.

    .. code-block:: python
        :caption: Example usage

        class ExampleActor(SubcommandsActor):
            def __init__(self, extra, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.extra = extra

            def get_commands(self):
                return [
                    Command('ex1', 'Description')(Example1Actor(self.extra)),
                    Command('ex2', 'Description')(Example2Actor(self.extra)),
                ]
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._parser = None

    def setup_parser(self, parent_parser):
        """
        :meta private:
        """
        self._parser = parent_parser
        parser = CommandParser()(self.get_commands())
        parser.setup_parser(parent_parser)

    def get_commands(self):
        """
        Return list of commands.

        :return: List of commands.
        :rtype: list of (Command or CommandGroup)
        """

        return []

    def __call__(self):
        self._parser.print_help()


class Command(object):
    """
    Command that can be run through CLI.

    .. code-block:: python
        :caption: Example usage - Command takes an Actor

        Command('command-name', 'description', Actor())

    .. code-block:: python
        :caption: Example usage - Command takes CommandParser

        Command('nested-command', 'Description', CommandParser()([
            Command('command-name', 'Description', Actor()),
        ]))
    """

    def __init__(self, name, help_message, handler, **add_parser_kwargs):
        """
        :param name: CLI command name. The command is executed if the name
            is provided in CLI arguments.
        :type name: str
        :param help_message: Help message visible in usage description.
        :type help_message: str
        :param handler: Actor that is executed when the command is run.
        :type handler: Actor
        :param \\*\\*add_parser_kwargs: Additional keyword arguments passed to
            :class:`argparse.Parser.add_parser`
        :type \\*\\*add_parser_kwargs: dict of str:any

        .. note::
            The default formatter class passed to ``argparse.Parser.add_parser``
            is ``argparse.RawTextHelpFormatter``. You can override it with
            ``formatter_class`` option. E.g.
            ``formatter_class=argparse.ArgumentDefaultsHelpFormatter``.
        """

        self.handler = handler
        self.name = name
        self.help = help_message
        self.kwargs = add_parser_kwargs

    def setup_parser(self, parent_parser):
        """
        Add new command parser to the parent parser.

        :param parent_parser: Parent parser.
        :type parent_parser: argparse.Parser
        """

        check_instance(self.handler, (Actor, CommandParser))

        parser_args = {
            'formatter_class': argparse.RawTextHelpFormatter
        }
        parser_args.update(self.kwargs)

        parser = parent_parser.add_parser(
            self.name, help=self.help,
            **parser_args
        )

        if isinstance(self.handler, CommandParser):
            parser.set_defaults(func=parser)
        else:
            parser.set_defaults(func=self.handler)

        self.handler.setup_parser(parser)


class CommandParser(object):
    """
    Comand parser.

    This is the root element for CLI command list.

    .. code-block:: python
        :caption: Example usage

        parser = argparse.ArgumentParser()

        CommandParser('Test Commands')([
            Command('ex1', 'Example 1', Actor()),
            CommandGroup('Below are nested commands')([
                Command('nested', 'Commands can be nested', CommandParser()([
                    Command('test2', 'Example 2', Actor()),
                ]))
            ])
        ]).setup_parser(parser)

        # ->
        # Test Commands:
        # COMMANDS
        #    test1               Example 1
        #    Below are nested commands
        #      nested            Commands can be nested

    It will setup the argument parser and make sure that all command handlers
    are set correctly.
    """

    def __init__(self, title=None, metavar='COMMANDS', **kwargs):
        """
        :param title: Title visible in help message, defaults to None
        :type title: str, optional
        :param metavar: Metavar name used for positional argument,
            defaults to 'COMMANDS'
        :type metavar: str, optional
        """

        self.title = title
        self.metavar = metavar
        self.kwargs = kwargs
        self.commands = []

    def setup_parser(self, parent_parser):
        """
        Setup command parsers on the parent parser.

        :param parent_parser: Parent parser.
        :type parent_parser: argparse.Parser
        :return: Command subparser.
        :rtype: argparse.Parser
        """

        subparser = parent_parser.add_subparsers(
            action=SubparsersAction,
            title=self.title,
            metavar=self.metavar,
            **self.kwargs
        )

        self._setup_commands_parsers(subparser, self.commands)
        return subparser

    def _setup_commands_parsers(self, parent_parser, children):
        for child in children:
            check_instance(child, (list, Command, CommandGroup))

            if type(child) == list:
                self._setup_commands_parsers(parent_parser, child)
                continue

            child.setup_parser(parent_parser)

    def __call__(self, commands):
        """
        Set command list.

        :param commands: List of commands to handle.
        :type commands: list of (Command or CommandGroup)
        :return: Self.
        :rtype: CommandParser
        """

        self.commands += get_as_list(commands)
        return self


class CommandGroup(CommandParser):
    """
    Adding commands to a command group will group them together under common
    descriptions.

    See :class:`CommandParser` for example usage.
    """

    def __init__(self, title, *args, **kwargs):
        """
        :param title: Group title
        :type title: str
        """

        super().__init__(title=title, *args, **kwargs)

    def setup_parser(self, parent_parser):
        """
        Setup command parsers on the parent parser.

        :param parent_parser: Parent parser.
        :type parent_parser: argparse.Parser
        :return: Command subparser.
        :rtype: argparse.Parser
        """

        group = parent_parser.add_parser_group(self.title)

        self._setup_commands_parsers(group, self.commands)
        return group
