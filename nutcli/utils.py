import inspect
import re
import types

import colorama

import nutcli


def check_instance(obj, allowed_classes):
    """
    Check object instance and raise a :class:`ValueError` if it is not instance
    of one of ``allowed_classes``.

    :param obj: Object to check.
    :type obj: any
    :param allowed_classes: Tuple of allowed classes.
    :type allowed_classes: class or tuple of class
    :raises ValueError: Object is not instance of any allowed class.
    """

    if isinstance(obj, allowed_classes):
        return

    raise ValueError('Expected instance of {}, got {}'.format(
        ', '.join([cls.__name__ for cls in get_as_list(allowed_classes)]),
        obj.__class__
    ))


def get_as_list(arg):
    """
    Return value as list.

        - list is returned as is
        - tuple is converted to list
        - anything else is returned as ``[arg]``

    :param arg: Value that will be returned as list.
    :type arg: any
    :return: Value as list.
    :rtype: list
    """

    if isinstance(arg, list):
        return arg
    elif isinstance(arg, tuple):
        return list(arg)
    elif arg is None:
        return []
    else:
        return [arg]


def dict_to_namespace(d):
    """
    Recursively convert dictionary into a namespace.

    :param d: The dictionary.
    :type d: dict
    :return: Namespace.
    :rtype: types.SimpleNamespace
    """

    def _dict_to_namespace(d):
        if d is None or type(d) != dict:
            return d

        ns = types.SimpleNamespace()
        for key, value in d.items():
            setattr(ns, key, _dict_to_namespace(value))

        return ns

    if d is None or type(d) != dict:
        raise ValueError('Input is not a dictionary')

    return _dict_to_namespace(d)


class Colorize(object):
    """
    Utilities to provide colorized output, using terminal colors.

    You can use ``colorama`` package to obtain the color definitions.

    Colors are enabled by default, you can disable the functionality with
    :func:`enabled`. All functions will return unchanged input if the
    colorization is disabled.
    """

    print_colors = True

    @classmethod
    def enabled(cls, enabled):
        """
        Enable or disable colors.

        :param enabled: state
        :type enabled: bool
        """

        cls.print_colors = enabled

    @classmethod
    def all(cls, fmt, *args):
        """
        Surround ``fmt`` with provided colors.

        .. code-block:: python
            :caption: Example usage

            str = Colorize.all(
                'hello world', colorama.Fore.RED, colorama.Style.BRIGHT
            )
            print(str)
            # -> Red and bold 'hello world'

        :param fmt: String to format.
        :type fmt: str
        :param \\*args: Color specifications.
        :type \\*args: str
        :return: Colorized string.
        :rtype: str
        """

        if not cls.print_colors or not fmt:
            return fmt

        reset = colorama.Style.RESET_ALL
        colors = ''.join(args)
        return f'{reset}{colors}{fmt}{reset}'

    @classmethod
    def bold(cls, fmt):
        """
        Make ``fmt`` bold.

        .. code-block:: python
            :caption: Example usage

            str = Colorize.bold('hello world')
            print(str)
            # -> Bold 'hello world'

        :param fmt: String to format.
        :type fmt: str
        :return: Colorized string.
        :rtype: str
        """

        return cls.all(fmt, colorama.Style.BRIGHT)

    @classmethod
    def re(cls, fmt, pattern, *args):
        """
        Colorize all matches found in ``fmt`` using regular expression.

        .. code-block:: python
            :caption: Example usage

            str = Colorize.re('hello', r'(.*)', colorama.Style.RED)
            print(str) # -> Red 'hello'

            str = Colorize.re(
                'hello', r'h(e)ll(o)',
                colorama.Fore.RED,
                [colorama.Fore.BLUE, colorama.Style.BRIGHT]
            )
            print(str) # -> 'hello' with red 'e' and blue and bold 'o'

        :param fmt: String to format.
        :type fmt: str
        :param pattern: Plain or compiled regular expression.
        :type pattern: str or type(re.compile(r''))
        :param \\*args: Color specifications.
            i-th match is colored with i-th element
        :type \\*args: str or list of str
        :return: Colorized string.
        :rtype: str
        """

        if not cls.print_colors:
            return fmt

        def replace(match):
            # (start, end, group)
            slices = []

            # Slice the match to avoid overlapping groups
            groups = [match.group(0)] + list(match.groups())
            for idx, _ in enumerate(groups[1:], start=1):
                (start, end) = match.span(idx)

                # This is the last slice, it does not overlap
                if idx >= len(groups) - 1:
                    slices.append((start, end, idx))
                    break

                # Find overlapping groups
                overlaps = []
                for nextidx, _ in enumerate(groups[idx + 1:], start=idx + 1):
                    if match.start(nextidx) >= end:
                        break

                    overlaps.append(nextidx)

                # Create the slices
                if not overlaps:
                    slices.append((start, end, idx))
                    continue

                for overlap_idx, group_idx in enumerate(overlaps):
                    # First overlap
                    if overlap_idx == 0:
                        slices.append((start, match.start(group_idx), idx))

                    # Last overlap
                    if overlap_idx == len(overlaps) - 1:
                        slices.append((match.end(group_idx), end, idx))

                    # Inside overlap
                    if overlap_idx != 0 and overlap_idx != len(overlaps) - 1:
                        slices.append((match.end(group_idx - 1), match.start(group_idx + 1), idx))

            # Sort slices
            slices.sort()

            # Generate replacement
            lastpos = match.start()
            result = ''

            for part in slices:
                (start, end, idx) = part

                # Normalize index to styles
                idx = idx - 1

                if idx >= len(args):
                    break

                result += fmt[lastpos:start]
                style = args[idx] if type(args[idx]) == list else [args[idx]]
                result += cls.all(fmt[start:end], *style)
                lastpos = end

            result += fmt[lastpos:match.end()]
            return result

        compiled = re.compile(pattern) if type(pattern) == str else pattern
        return compiled.sub(replace, fmt)


class LogExecutionPrinter(object):
    """
    Print exact function call to the information logs.

    You can use this in conjunction with
    :class:`nutcli.decorators.LogExecution` and
    :class:`nutcli.decorators.SideEffect`.
    """

    def __init__(self, skip_self=True, logger=None):
        """
        :param skip_self: If True the first parameter named 'self' will be
            skipped, defaults to True
        :type skip_self: bool, optional
        :param logger: Logger, defaults to None (= :class:`nutcli.message`)
        :type logger: logger, optional
        """
        self.skip_self = skip_self
        self.logger = logger if logger is not None else nutcli.message

    def flat_kwargs(self, kwargs):
        return ', '.join(
            '{!s}={!r}'.format(key, value) for key, value in kwargs.items()
        )

    def flat_args(self, args):
        return ', '.join(repr(x) for x in args)

    def sanitize_args(self, function, args):
        if not self.skip_self:
            return args

        if '.' in function.__qualname__:
            spec = inspect.getfullargspec(function)
            if spec.args and spec.args[0] == 'self':
                return args[1:]

        return args

    def log_call(self, function, args, kwargs):
        args = get_as_list(args)
        args = self.sanitize_args(function, args)

        flatargs = self.flat_args(args)
        flatkwargs = self.flat_kwargs(kwargs)

        separator = ', '
        if not flatargs or not flatkwargs:
            separator = ''

        self.logger.info(f'{function.__qualname__}({flatargs}{separator}{flatkwargs})')

    def __call__(self, message, function, args, kwargs):
        """
        Produce the log message.

        :param message: The message.
        :type message: str
        :param function: Function that was called.
        :type function: callable
        :param args: Function positional arguments.
        :type args: list of any
        :param kwargs: Function keyword arguments.
        :type kwargs: dict of str:any

        If ``message`` is not ``None`` then only the ``message`` is printed
        to the log. Otherwise the function execution is produced.
        """
        if message is not None:
            self.logger.info(message)
            return

        self.log_call(function, args, kwargs)
