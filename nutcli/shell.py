import copy
import os
import subprocess
import textwrap
from enum import Enum

import colorama

import nutcli
from nutcli.decorators import Identity, LogExecution, SideEffect
from nutcli.utils import Colorize, LogExecutionPrinter, get_as_list


class Shell(object):
    """
    Run commands in closed shell environment.

    .. code-block:: python
        :caption: Example usage

        sh = Shell()
        sh('echo "Hello World!"')
        sh(['/bin/bash', '-c', 'echo "Hello World!"'])
        she('echo $HELLO', env={'HELLO': 'World!'})
    """

    class Effect(Enum):
        """
        Sometimes, it is desirable to produce some additional effect such as
        a log message when the command is run. These values control the effect.
        """

        Blank = 0
        """
        Nothing is done when the command is executed.
        """

        LogExecution = 1
        """
        Each call is logged into the information log if it is enabled in
        :class:`nutcli.decorators.LogExecution`.
        """

        SideEffect = 2
        """
        Each call is logged into the information log if it is enabled in
        :class:`nutcli.decorators.LogExecution`. And the command is not
        run at all if dry run is enabled in
        :class:`nutcli.decorators.SideEffect`.
        """

    def __init__(
        self,
        cwd=None,
        env=None,
        clear_env=False,
        shell=None,
        default_effect=Effect.SideEffect,
        logger=None
    ):
        """
        :param cwd: Default working directory, defaults to None
            (= current working directory)
        :type cwd: str, optional
        :param env: Additional environment values, defaults to None
        :type env: dict of str:str, optional
        :param clear_env: If True, current shell environment is ignored,
            defaults to False
        :type clear_env: bool, optional
        :param shell: Shell that will be used to execute commands, defaults
            to None (= ['/bin/bash', '-c'])
        :type shell: list of str, optional
        :param default_effect: Default execution effect, defaults to
            :class:`Effect.SideEffect`
        :type default_effect: Effect, optional
        :param logger: Logger, defaults to None (= :class:`nutcli.message`)
        :type logger: logger, optional
        """

        self.cwd = cwd if cwd is not None else os.getcwd()
        self.shell = shell if shell is not None else ['/bin/bash', '-c']
        self.default_effect = default_effect
        self.logger = logger if logger is not None else nutcli.message

        self.env = ShellEnvironment(clear_env)
        self.env.set(env)

    def __apply_defaults(self, **kwargs):
        defaults = {
            'text': True,
            'capture_output': False,
            'check': True,
            'cwd': self.cwd
        }

        return {**defaults, **kwargs}

    def __decorator(self, effect, result, message):
        if effect == self.Effect.Blank or effect is None:
            return Identity
        elif effect == self.Effect.LogExecution:
            return LogExecution(
                message=message,
                printer=_ShellCommandPrinter(logger=self.logger)
            )
        elif effect == self.Effect.SideEffect:
            return SideEffect(
                message=message,
                returns=ShellResult(0) if not result else result,
                printer=_ShellCommandPrinter(logger=self.logger)
            )
        else:
            raise ValueError(f'Unknown shell execution effect: {effect}')

    def __call__(
        self,
        command,
        env=None,
        effect=None,
        dry_run_result=None,
        execution_message=None,
        **kwargs
    ):
        """
        Execute shell command.

        :param command: Command to execute
        :type command: str or list of str
        :param env: Additional environment variables, defaults to None
        :type env: dict of str:str, optional
        :param effect: Execution effect, defaults to None
            (= value provided in constructor)
        :type effect: Effect, optional
        :param dry_run_result: Result for dry run call if ``effect`` is set
            to ``SideEffect``, defaults to None
        :type dry_run_result: any, optional
        :param execution_message: Log execution message if ``effect`` is set
            to ``LogExecution`` or ``SideEffect``, defaults to None
        :type execution_message: str, optional
        :raises ShellCommandError: Command returned non-zero status code
        :raises ShellTimeoutError: Command did not finish in time
        :return: Shell result object.
        :rtype: ShellResult

        Command may be either a list of command and its arguments or a string
        representing a full command line. If it is a list it is run as is via
        ``subproccess.run()``, if it is a string it is run inside a shell as:

            - ``[shell, command]``, e.g. ``['/bin/bash', '-c', command]``

        Additional keyword arguments can be specified to be forwarded to
        ``subprocess.run()`` call. By default ``text`` mode is set to true,
        therefore if you capture output via ``capture_output`` or other means,
        it is considered to be a text and is decoded as utf-8 text.

        Common ``subprocess.run()`` arguments:

            - ``capture_output`` {bool} -- Capture stdout and stderr.
            - ``cwd`` {string} -- Change working directory.
            - ``timeout`` -- timeout in seconds

        .. note::
            See python documentation for more:

                - https://docs.python.org/3/library/subprocess.html
        """

        if effect is None:
            effect = self.default_effect

        real_env = self.env.clone().set(env)
        real_args = self.__apply_defaults(**kwargs)
        decorator = self.__decorator(effect, dry_run_result, execution_message)

        if type(command) == str:
            command = textwrap.dedent(command).strip()

        @decorator
        def execute(command, env, **kwargs):
            if type(command) is list:
                real_command = command
            else:
                real_command = [*self.shell, command]

            result = subprocess.run(real_command, env=env.get(), **kwargs)
            return ShellResult(result.returncode, result.stdout, result.stderr)

        try:
            return execute(command, env=real_env, **real_args)
        except subprocess.CalledProcessError as e:
            raise ShellCommandError(
                rc=e.returncode,
                cmd=command,
                cwd=real_args['cwd'],
                env=real_env,
                stdout=e.output,
                stderr=e.stderr
            ) from None
        except subprocess.TimeoutExpired as e:
            # e.timeout does not always contain integer so we have to round it
            raise ShellTimeoutError(
                timeout=real_args.get('timeout', round(e.timeout)),
                cmd=command,
                cwd=real_args['cwd'],
                env=real_env,
                stdout=e.output,
                stderr=e.stderr
            ) from None

    def clone(self):
        """Create a deep copy of self.

        Returns:
            ShellEnvironment -- Self deep copy.
        """

        return copy.deepcopy(self)


class ShellResult(object):
    """Result of successful shell command execution."""

    def __init__(self, rc, stdout=None, stderr=None):
        """
        :param rc: Command return code
        :type rc: Int
        :param stdout: Captured command standard output stream
        :type stdout: bytes or str
        :param stderr: Captured command standard error stream.
        :type stderr: bytes or str
        """

        self.rc = rc
        self.stdout = stdout
        self.stderr = stderr


class ShellEnvironment(object):
    """Manage copy of shell environment."""

    def __init__(self, clear_env=False):
        """
        :param clear_env: If True, current shell environment is ignored, defaults to False
        :type clear_env: bool, optional
        """

        self.default = os.environ.copy() if not clear_env else {}
        self.overrides = {}

    def set(self, env):
        """
        Add values to the environment.

        :param env: Additional environment.
        :type env: dict of str:str
        :return: self
        :rtype: ShellEnvironment
        """

        if env is not None:
            self.overrides.update(env)

        return self

    def get(self):
        """
        Get new copy of this environment as a dictionary.

        :return: This environment as a dictionary
        :rtype: dict of str:str
        """

        return {**self.default, **self.overrides}

    def get_overrides(self):
        """
        Get only values that were added to the original environment.

        :return: Additional environment as a dictionary
        :rtype: dict of str:str
        """

        return self.overrides

    def clone(self):
        """
        Get a deep copy of this object.

        :return: Deep copy of self.
        :rtype: ShellEnvironment
        """

        return copy.deepcopy(self)


class ShellError(Exception):
    """Provide information about shell error."""

    def __init__(self, message, cmd, cwd, env, stdout, stderr):
        """
        :param message: Error message
        :type message: str
        :param cmd: Failed command
        :type cmd: str or list of str
        :param cwd: Command working directory
        :type cwd: str
        :param env: Command environment
        :type env: ShellEnvironment
        :param stdout: Captured command standard output stream
        :type stdout: bytes or str
        :param stderr: Captured command standard error stream.
        :type stderr: bytes or str
        """

        super().__init__(message)

        self.cmd = cmd
        self.cwd = cwd if cwd is not None else os.getcwd()
        self.env = env
        self.stdout = stdout
        self.stderr = stderr

    @property
    def pretty_message(self):
        """
        Get formatted error message. It is returned as list of string where
        each item represents one line of the message.

        :return: Error message lines.
        :rtype: list of str
        """

        return _ShellCommandPrinter().get_pretty(self.cmd, self.env, self.cwd)


class ShellCommandError(ShellError):
    """Provide information about failed command."""

    def __init__(self, rc, cmd, cwd, env, stdout, stderr):
        """
        :param rc: Command return code
        :type rc: int
        :param cmd: Failed command
        :type cmd: str or list of str
        :param cwd: Command working directory
        :type cwd: str
        :param env: Command environment
        :type env: ShellEnvironment
        :param stdout: Captured command standard output stream
        :type stdout: bytes or str
        :param stderr: Captured command standard error stream.
        :type stderr: bytes or str
        """

        super().__init__(
            f'Command returned non-zero status code: {rc}',
            cmd, cwd, env, stdout, stderr
        )

        self.rc = rc

    @property
    def pretty_message(self):
        """
        Get formatted error message. It is returned as list of string where
        each item represents one line of the message.

        :return: Error message lines.
        :rtype: list of str
        """

        message = [Colorize.bold(f'The following command exited with: {self.rc}')]
        message += super().pretty_message
        return message


class ShellTimeoutError(ShellError):
    """Provide information about command that did not end in set time."""

    def __init__(self, timeout, cmd, cwd, env, stdout, stderr):
        """
        :param timeout: Timeout value in seconds
        :type timeout: int
        :param cmd: Failed command
        :type cmd: str or list of str
        :param cwd: Command working directory
        :type cwd: str
        :param env: Command environment
        :type env: ShellEnvironment
        :param stdout: Captured command standard output stream
        :type stdout: bytes or str
        :param stderr: Captured command standard error stream.
        :type stderr: bytes or str
        """

        super().__init__(
            f'Command did not finish in time: {timeout} seconds',
            cmd, cwd, env, stdout, stderr
        )

        self.timeout = timeout

    @property
    def pretty_message(self):
        """
        Get formatted error message. It is returned as list of string where
        each item represents one line of the message.

        :return: Error message lines.
        :rtype: list of str
        """

        message = [Colorize.bold(f'The following command timed out ({self.timeout} seconds)')]
        message += super().pretty_message
        return message


class _ShellCommandPrinter(LogExecutionPrinter):

    def __init__(self, logger=None):
        super().__init__(False, logger=logger)

    def get_pretty(self, command, env, cwd):
        env = ' '.join(
            Colorize.re(
                '{!s}={!r}', r'({!s}=)({!r})',
                [colorama.Fore.MAGENTA, colorama.Style.BRIGHT]
            ).format(k, v) for k, v in env.get_overrides().items()
        )

        if type(command) == str:
            command = command.strip()
            if len(command.split('\n')) > 1:
                command = '(see listing below)\n\n' + textwrap.indent(command, '  ') + '\n'

        messages = [
            ('[shell] Working directory: {}', cwd),
            ('[shell] Environment: {}', env),
            ('[shell] Command: {}', command),
        ]

        pretty = []
        for (message, arg) in messages:
            pretty.append(
                Colorize.re(
                    message, r'(\[[^\]]*\]) ([^:]*:)',
                    [colorama.Fore.BLUE, colorama.Style.BRIGHT],
                    colorama.Style.BRIGHT
                ).format(arg))

        return pretty

    def __call__(self, message, function, args, kwargs):
        if message is None:
            message = self.get_pretty(args[0], kwargs['env'], kwargs['cwd'])

        message = get_as_list(message)
        for msg in message:
            self.logger.info(msg)
