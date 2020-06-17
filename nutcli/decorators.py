import functools
import re
import signal

from nutcli.exceptions import TimeoutError
from nutcli.utils import LogExecutionPrinter


def Identity(function):
    """
    Identity decorator. It does nothing to the decorated function.

    It can be used to simplify the code.

    .. code-block:: python
        :caption: Example usage

        def identity_example(ignore_errors):
            decorator = IgnoreErrors if ignore_errors else Identity

            @decorator
            def do_something():
                pass
    """
    @functools.wraps(function)
    def wrapper(*args, **kwargs):
        return function(*args, **kwargs)

    return wrapper


def IgnoreErrors(function):
    """
    All exceptions raised from the decorated function will be ignored.

    .. code-block:: python
        :caption: Example usage

        @IgnoreErrors
        def raise_error(ignore_errors):
            raise Exception('This will be ignored.')

        raise_error()
    """
    @functools.wraps(function)
    def wrapper(*args, **kwargs):
        try:
            return function(*args, **kwargs)
        except Exception:
            return None

    return wrapper


class Timeout(object):
    """
    A :class:`nutcli.exceptions.TimeoutError` is risen if the decoration
    function does not finish in time.

    The code is based on timeout-decorator:
    - https://github.com/pnpnpn/timeout-decorator

    .. code-block:: python
        :caption: Example usage

        @Timeout(2)
        def be_slow():
            time.sleep(5)

        try:
            be_slow()
        except nutcli.exceptions.TimeoutError as e:
            print(str(e))
    """

    def __init__(self, timeout=None, message=None):
        """
        :param timeout: Timeout in seconds or a simple time format, defaults
            to None.
        :type timeout: int, str, optional
        :param message: Error message, defaults to None
        :type message: str, optional

        Parameter ``timeout`` may contains one of the following values:

        - :code:`None`: No timeout is applied
        - :code:`int`: Number of seconds
        - :code:`'X seconds Y minutes Z hours'`: Simple natural time
          specifications

            + :code:`X`, :code:`Y` and :code:`Z` can be :code:`float`
            + Each of :code:`seconds`, :code:`minutes` and :code:`hours`
              can be omitted
            + Suffix :code:`s` can be omitted

        Parameter ``message`` is passed to
        :class:`nutcli.exceptions.TimeoutError` constructor.
        """
        self.timeout = timeout
        self.message = message if message is not None else 'Operation timed out.'
        self.seconds = self.__to_seconds(timeout)

    def __to_seconds(self, timeout):
        if timeout is None:
            return None
        elif type(timeout) == int:
            return timeout
        elif type(timeout) != str:
            raise ValueError(f'Unexpected timeout format: {timeout}')

        matches = re.findall(r'(([\d\.]+)\W*(hours?|minutes?|seconds?)?)', timeout)
        if not matches:
            raise ValueError(f'Unknown timeout format: {timeout}')

        seconds = 0
        for m in matches:
            (_, time, unit) = m
            if unit.startswith('h'):
                seconds += int(float(time) * 60 * 60)
            elif unit.startswith('m'):
                seconds += int(float(time) * 60)
            else:
                seconds += int(time)

        return seconds

    def __signal_handler(self, signum, frame):
        raise TimeoutError(self.seconds, self.message)

    def __call__(self, function):
        if not self.seconds:
            return function

        @functools.wraps(function)
        def wrapper(*args, **kwargs):
            old_handler = signal.signal(signal.SIGALRM, self.__signal_handler)
            old_timer = signal.setitimer(signal.ITIMER_REAL, self.seconds)
            try:
                return function(*args, **kwargs)
            finally:
                signal.setitimer(signal.ITIMER_REAL, *old_timer)
                signal.signal(signal.SIGALRM, old_handler)

        return wrapper


class LogExecution(object):
    """
    If enabled, each call of decorated method will produce an info log message.

    .. code-block:: python
        :caption: Example usage

        @LogExecution()
        def example():
            pass

        LogExecution.enabled(True)

        example()
        # -> INFO example()
    """

    should_log_execution = False

    def __init__(self, message=None, printer=None, logger=None):
        """
        :param message: Message to log, defaults to None
        :type message: str, optional
        :param printer: Execution printer, defaults to None
        :type printer: :class:`nutcli.utils.LogExecutionPrinter`, optional
        :param logger: Logger, defaults to None (= :class:`nutcli.message`)
        :type logger: logger, optional

        If ``printer`` is None then :class:`nutcli.utils.LogExecutionPrinter`
        is used. The ``printer`` will log the message using ``logger``.

        The default printer will either produce ``message`` if it is not
        :code:`None` or exact function call.
        """
        self.message = message
        self.printer = printer

        if self.printer is None:
            self.printer = LogExecutionPrinter(logger=logger)

    def log(self, function, args, kwargs):
        self.printer(self.message, function, args, kwargs)

    def __call__(self, function):
        @functools.wraps(function)
        def wrapper(*args, **kwargs):
            if self.should_log_execution:
                self.log(function, args, kwargs)
            return function(*args, **kwargs)

        return wrapper

    @classmethod
    def enabled(cls, enabled=True):
        """
        Enable or disable execution logging.

        :param enabled: The state, defaults to True
        :type enabled: bool, optional
        """
        cls.should_log_execution = enabled


class SideEffect(LogExecution):
    """
    If dry run is enabled the decorated function will not be run and only its
    execution is printed to the info log. The dry run can be enabled with
    :func:`dry_run`.

    .. note::
        Since this inherits from :class:`LogExecution` it will also produce
        a log execution message if it is enabled.

    .. code-block:: python
        :caption: Example usage

        @SideEffect()
        def example():
            # remove files
            pass

        SideEffect.dry_run(True)

        example()
        # -> INFO example()
        # Files are not deleted, example() is not executed.
    """

    is_dry_run = False

    def __init__(self, message=None, returns=None, printer=None, logger=None):
        """
        :param message: Message to log, defaults to None
        :type message: str, optional
        :param returns: Return value of the decorated function if dry run
            is enabled, defaults to None
        :type returns: any, optional
        :param printer: Execution printer, defaults to LogExecutionPrinter()
        :type printer: :class:`nutcli.utils.LogExecutionPrinter`, optional
        :param logger: Logger, defaults to None (= :class:`nutcli.message`)
        :type logger: logger, optional

        If ``printer`` is None then :class:`nutcli.utils.LogExecutionPrinter`
        is used. The ``printer`` will log the message using ``logger``.

        The default printer will either produce ``message`` if it is not
        :code:`None` or exact function call.

        Call to the decorated function will return ``returns`` if dry run
        is enabled.
        """
        super().__init__(message, printer, logger)

        self.returns = returns

    def __call__(self, function):
        @functools.wraps(function)
        def wrapper(*args, **kwargs):
            if self.is_dry_run or self.should_log_execution:
                self.log(function, args, kwargs)

            if not self.is_dry_run:
                return function(*args, **kwargs)
            else:
                return self.returns

        return wrapper

    @classmethod
    def dry_run(cls, enabled=True):
        """
        Enable or disable dry run.

        :param enabled: The state, defaults to True
        :type enabled: bool, optional
        """
        cls.is_dry_run = enabled
