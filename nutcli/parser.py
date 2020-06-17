import argparse
from collections import OrderedDict

from nutcli.utils import get_as_list


# Based on patch from https://bugs.python.org/issue9341
class SubparsersAction(argparse._SubParsersAction):
    """
    Provide a subparser action that can create subparsers with ability of
    grouping arguments.

    It is based on the patch from:

        - https://bugs.python.org/issue9341

    You most probably do not need to use this yourself. Hovewer, you can see
    it in action in the source code of :class:`nutcli.commands.CommandParser`.
    """

    class _PseudoGroup(argparse.Action):

        def __init__(self, container, title):
            super().__init__(option_strings=[], dest=title)
            self.container = container
            self._choices_actions = []

        def add_parser(self, name, **kwargs):
            # add the parser to the main Action, but move the pseudo action
            # in the group's own list
            parser = self.container.add_parser(name, **kwargs)
            choice_action = self.container._choices_actions.pop()
            self._choices_actions.append(choice_action)
            return parser

        def _get_subactions(self):
            return self._choices_actions

        def add_parser_group(self, title):
            # the formatter can handle recursive subgroups
            grp = SubparsersAction._PseudoGroup(self, title)
            self._choices_actions.append(grp)
            return grp

    def add_parser_group(self, title):
        """
        Add new parser group.

        :param title: Title.
        :type title: str
        :return: Parser group that can have additional parsers attached.
        :rtype: ``argparse.Action`` extended with ``add_parser`` method
        """
        grp = self._PseudoGroup(self, title)
        self._choices_actions.append(grp)
        return grp


class UniqueAppendAction(argparse.Action):
    """
    Append value to a list and make sure there are no duplicates.

    .. code-block:: python
        :caption: Example usage

        parser = argparse.ArgumentParser()
        parser.add_argument(
            'list', nargs='*', choices=['all', 'a', 'b', 'c'],
            action=UniqueAppendAction, default='all',
            help='Choose values. Multiple values may be set. (Default "all")'
        )

        args = parser.parse_args(['--list', 'a', '--list', 'b', '--list', 'a'])
        print(args.list)
        # -> ['a', 'b']
    """

    def __call__(self, parser, namespace, values, option_string=None):
        values = get_as_list(self._get_values(values))
        if not hasattr(namespace, self.dest):
            setattr(namespace, self.dest, values)

        current = getattr(namespace, self.dest)

        # Default value is set automatically, we must unset it.
        if current == self.default:
            current = None

        current = get_as_list(current)
        values = list(OrderedDict.fromkeys(current + values))
        setattr(namespace, self.dest, values)

    def _get_values(self, values):
        return values


class UniqueAppendConstAction(UniqueAppendAction):
    """
    Append const value to a list and make sure there are no duplicates.

    .. code-block:: python
        :caption: Example usage

        parser = argparse.ArgumentParser()

        parser.add_argument(
            '-f', '--failed', const='failed', dest='filter',
            action=UniqueAppendConstAction, help='Show failed items.'
        )

        parser.add_argument(
            '-a', '--aborted', const='aborted', dest='filter',
            action=UniqueAppendConstAction, help='Show aborted items.'
        )

        parser.add_argument(
            '-s', '--successful', const='success', dest='filter',
            action=UniqueAppendConstAction, help='Show successful items.'
        )

        args = parser.parse_args(['-f', '-a', '-s', '-f'])
        print(args.filter)
        # -> ['failed', 'aborted', 'success']
    """

    def __init__(self, *args, **kwargs):
        kwargs['nargs'] = 0
        super().__init__(*args, **kwargs)

    def _get_values(self, values):
        return self.const


class NegateAction(argparse.Action):
    """
    Implements toggle argumnets.

    Stores True if --arg is present, False if --no-arg is present.

    .. code-block:: python
        :caption: Example usage

        parser = argparse.ArgumentParser()

        # You can set default value using 'default' parameter.
        parser.add_argument(
            '--arg', '--no-arg', action=NegateAction, help='Enable/disable arg.'
        )

        args = parser.parse_args([])
        print(args.arg)
        # -> None

        args = parser.parse_args(['--arg'])
        print(args.arg)
        # -> True

        args = parser.parse_args(['--no-arg'])
        print(args.arg)
        # -> False
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **{**kwargs, 'nargs': 0})

    def __call__(self, parser, ns, values, option):
        dest = self.dest
        if dest is None:
            dest = option[5:] if option[2:5] == 'no-' else option[2:]

        setattr(ns, dest, option[2:4] != 'no')
