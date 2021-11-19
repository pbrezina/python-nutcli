import datetime
import functools
import inspect
import sys

import colorama

import nutcli
from nutcli.decorators import IgnoreErrors, Timeout
from nutcli.utils import Colorize


class Task(object):
    """
    Execute operation as a single task.

    It can create a nicely formatted output of series of tasks in combination
    with :class:`TaskList`.

    .. note::
        See :class:`TaskList` for example usage.
    """

    def __init__(
        self,
        name=None,
        ignore_errors=False,
        always=False,
        enabled=True,
        timeout=None,
        logger=None
    ):
        """
        :param name: Task name, defaults to None
        :type name: str, optional
        :param ignore_errors: If True, all errors will be ignored,
            defaults to False
        :type ignore_errors: bool, optional
        :param always: If True, it will be run inside a :class:`TaskList` even
            if some previous tasks raised an exception, defaults to False
        :type always: bool, optional
        :param enabled: If False, this task will not execute its handler,
            defaults to True
        :type enabled: bool, optional
        :param timeout: Timeout in seconds or specific format (see
            :class:`nutcli.decorators.Timeout`), defaults to None
        :type timeout: int or str, optional
        :param logger: Logger, defaults to (= :class:`nutcli.message`)
        :type logger: logger, optional
        """
        self.name = name if name is not None else ''
        self.ignore_errors = ignore_errors
        self.always = always
        self.enabled = enabled
        self.timeout = timeout

        self.handler = None
        self.args = []
        self.kwargs = {}

        self.__logger = logger if logger is not None else nutcli.message
        self._parent = None

    def _set_parent(self, parent):
        self._parent = parent

    @property
    def _log_prefix(self):
        if self._parent is None:
            return ''

        return self._parent._log_prefix + '  '

    @property
    def _log_prefix_len(self):
        return len(self._log_prefix) + getattr(
            self.__logger, '_log_prefix_len', 0
        )

    def _log_message(self, fn, msg, args, kwargs):
        fn(self._log_prefix + msg, *args, **kwargs)

    def debug(self, msg, *args, **kwargs):
        """
        Log a debug message.

        :param msg: The message.
        :type msg: str
        """

        self._log_message(self.__logger.debug, msg, args, kwargs)

    def info(self, msg, *args, **kwargs):
        """
        Log an information message.

        :param msg: The message.
        :type msg: str
        """

        self._log_message(self.__logger.info, msg, args, kwargs)

    def warning(self, msg, *args, **kwargs):
        """
        Log a warning message.

        :param msg: The message.
        :type msg: str
        """

        self._log_message(self.__logger.warning, msg, args, kwargs)

    def error(self, msg, *args, **kwargs):
        """
        Log an error message.

        :param msg: The message.
        :type msg: str
        """

        self._log_message(self.__logger.error, msg, args, kwargs)

    def critical(self, msg, *args, **kwargs):
        """
        Log an critical message.

        :param msg: The message.
        :type msg: str
        """

        self._log_message(self.__logger.critical, msg, args, kwargs)

    def __real_handler(self, overrides):
        if not self.handler:
            raise ValueError('No task handler specified.')

        kwargs = {**self.__dict__, **overrides}

        real = self.handler

        if kwargs['ignore_errors']:
            real = IgnoreErrors(real)

        if kwargs['timeout'] is not None:
            real = Timeout(kwargs['timeout'])(real)

        return real

    def __real_args(self):
        if not self.handler:
            raise ValueError('No task handler specified.')

        spec = inspect.getfullargspec(self.handler)

        # Check if 'task' parameter is already set in positional parameters
        if 'task' in spec.args:
            task_index = spec.args.index('task')
            if len(self.args) > task_index:
                return (self.args, self.kwargs)

        # Check if 'task' parameter is already set in keyword parameters
        if 'task' in self.kwargs:
            return (self.args, self.kwargs)

        # Not set it either, add it if requested
        if 'task' in spec.args or spec.varkw is not None:
            return (self.args, {**self.kwargs, 'task': self})

        return (self.args, self.kwargs)

    def execute(self, parent=None, **kwargs):
        """
        Execute the task's handler.

        Tasks can be nested. Logger is inherited from the parent
        if it is not ``None`` to produce nicely formatted logs.

        :param parent: Parent ``Task``, defaults to None
        :type parent: Task, optional
        """
        self._set_parent(parent)

        if not self.enabled:
            return

        (real_args, real_kwargs) = self.__real_args()
        self.__real_handler(kwargs)(*real_args, **real_kwargs)

    def __call__(self, function, *args, **kwargs):
        """
        Setup a function that will be executed by :func:`execute`.

        If the handler have ``task`` among parameters and this parameter is not
        set in neither positional nor keyword arguments it will be set to
        the task itself so the handler can access formatted logger functions.

        :param function: Task's handler.
        :type function: callable
        :return: Self.
        :rtype: Task
        """
        self.handler = function
        self.args = list(args)
        self.kwargs = kwargs

        return self

    @classmethod
    def Cleanup(cls, *args, **kwargs):
        """
        Create a finalizer.

        Creates a task that ignore all errors and is executed even if
        one of the previous tasks failed.

        :return: New task.
        :rtype: Task
        """
        return cls(*args, ignore_errors=True, always=True, **kwargs)


class TaskList(Task):
    """
    A task list.

    It can execute a list of task in series and provide nicely formatted
    log output.

    This class has wrappers around ``TaskList.tasks`` list methods therefore
    you can use TaskList instance as a list itself to easily add or remove
    single tasks.

    .. code-block:: python
        :caption: Example usage: Basic use case

        tasklist = TaskList()([
            Task('Task 1')(lambda task: task.info('Task 1')),
            Task('Task 2')(lambda task, arg: task.info(arg), 'Task 2'),
            Task('Task 3')(lambda task, arg: task.info(arg), arg='Task 3'),
        ])

        tasklist.execute()

        # ->
        # [1/3] Task 1
        #   Task 1
        # [2/3] Task 2
        #   Task 2
        # [3/3] Task 3
        #   Task 3

    .. code-block:: python
        :caption: Example usage: Nested tasks

        tasklist = TaskList('task-list')([
            Task('Task 1')(lambda task: task.info('Task 1')),
            Task('Task 2')(lambda task: task.info('Task 2')),
            TaskList('next-level')([
                Task('Task 3')(lambda task: task.info('Task 3')),
                Task('Task 4')(lambda task: task.info('Task 4')),
            ]),
            TaskList()([
                Task('Task 5')(lambda task: task.info('Tag can be empty')),
                Task('Task 6')(lambda task: task.info('It's up to you')),
            ])
        ])

        tasklist.execute()

        # ->
        # [task-list] [1/4] Task 1
        # [task-list]   Task 1
        # [task-list] [2/4] Task 2
        # [task-list]   Task 2
        # [task-list] [3/4]
        # [task-list]   [next-level] [1/2] Task 3
        # [task-list]   [next-level]   Task 3
        # [task-list]   [next-level] [2/2] Task 4
        # [task-list]   [next-level]   Task 4
        # [task-list] [4/4]
        # [task-list]   [1/2] Task 5
        # [task-list]     Tag can be empty
        # [task-list]   [2/2] Task 6
        # [task-list]     It's up to you

    .. code-block:: python
        :caption: Example usage: Finalizer

        def raise_task():
            raise Exception('Ooops')

        tasklist = TaskList('task-list')([
            Task('Task 1')(lambda task: task.info('I am doing something bad')),
            Task('Task 2')(raise_task),
            Task('Task 3')(lambda task: task.info('I was skipped')),
            Task.Cleanup('Task 4')(lambda task: task.info('Cleaning up'))
        ])

        tasklist.execute()

        # ->
        # [task-list] [1/4] Task 1
        # [task-list]   I am doing something bad
        # [task-list] [2/4] Task 2
        # [task-list] ERROR Exception: Ooops
        # [task-list] [3/4] Task 3 (skipped on error)
        # [task-list] [4/4] Task 4 (finalizing)
        # [task-list]   Cleaning up
    """

    def __init__(
        self,
        tag=None,
        name=None,
        ignore_errors=False,
        always=False,
        enabled=True,
        timeout=None,
        logger=None,
        duration=False
    ):
        """
        :param tag: Tag that will be visible on each log message,
            defaults to None
        :type tag: str, optional
        :param name: Task name, defaults to None
        :type name: str, optional
        :param ignore_errors: If True, all errors will be ignored,
            defaults to False
        :type ignore_errors: bool, optional
        :param always: If True, it will be run inside a :class:`TaskList` even
            if some previous tasks raised an exception, defaults to False
        :type always: bool, optional
        :param enabled: If False, this task will not execute its handler,
            defaults to True
        :type enabled: bool, optional
        :param timeout: Timeout in seconds or specific format (see
            :class:`nutcli.decorators.Timeout`), defaults to None
        :type timeout: int or str, optional
        :param logger: Logger, defaults to (= :class:`nutcli.message`)
        :type logger: logger, optional
        :param duration: If True, the time that the task list takes to finish
            is printed at the end, defaults to False
        :type duration: bool, optional
        """
        super().__init__(
            name, ignore_errors, always, enabled, timeout, logger
        )
        super().__call__(self._run_tasks)

        self.tag = tag
        self.duration = duration
        self.tasks = []

    @property
    def _log_prefix(self):
        tag = f'[{self.tag}] ' if self.tag is not None else ''

        if self._parent is None:
            return tag

        return self._parent._log_prefix + '  ' + tag

    def _run_tasks(self):
        error = None
        error_info = None

        enabled_tasks = [x for x in self.tasks if x.enabled]
        start = datetime.datetime.now()
        for idx, task in enumerate(enabled_tasks, start=1):
            msg = f'[{idx}/{len(enabled_tasks)}] {task.name}'

            if error is not None and not task.always:
                self.info(f'{msg} (skipped on error)')
                continue
            elif error is not None and task.always:
                self.info(f'{msg} (finalizing)')
                task.execute(parent=self, ignore_errors=True)
                continue

            self.info(msg)
            try:
                task.execute(parent=self)
            except BaseException as e:
                msg = Colorize.all(f'ERROR {e.__class__.__name__}', colorama.Fore.RED)
                self.error(f'{msg}: {str(e)}')
                error = e
                error_info = sys.exc_info()

        if self.duration:
            end = datetime.datetime.now()
            hours, remainder = divmod((end - start).total_seconds(), 3600)
            minutes, seconds = divmod(remainder, 60)
            self.info('Finished in {:02}:{:02}:{:02}'.format(
                int(hours), int(minutes), int(seconds)
            ))

        if error is not None:
            msg = Colorize.all(error.__class__.__name__, colorama.Fore.RED)
            self.error(f'Finished with error {msg}: {str(error)}')
            raise error.with_traceback(error_info[2])

    def __call__(self, tasks):
        """
        Add tasks to the list.

        :param tasks: List of tasks.
        :type: list of Task
        :return: Self.
        :rtype: TaskList
        """

        self.tasks += tasks if type(tasks) == list else [tasks]
        return self

    @functools.wraps(list.append)
    def append(self, item):
        return self.tasks.append(item)

    @functools.wraps(list.extend)
    def extend(self, item):
        return self.tasks.extend(item)

    @functools.wraps(list.insert)
    def insert(self, index, item):
        return self.tasks.insert(index, item)

    @functools.wraps(list.remove)
    def remove(self, item):
        return self.tasks.remove(item)

    @functools.wraps(list.pop)
    def pop(self, index=-1):
        return self.tasks.pop(index)

    @functools.wraps(list.clear)
    def clear(self):
        return self.tasks.clear()

    @functools.wraps(list.__len__)
    def __len__(self):
        return len(self.tasks)

    @functools.wraps(list.__getitem__)
    def __getitem__(self, key):
        return self.tasks[key]

    @functools.wraps(list.__setitem__)
    def __setitem__(self, key, value):
        self.tasks[key] = value

    @functools.wraps(list.__delitem__)
    def __delitem__(self, key):
        del self.tasks[key]

    @functools.wraps(list.__iter__)
    def __iter__(self):
        return self.tasks.__iter__()

    @functools.wraps(list.__contains__)
    def __contains__(self, item):
        return item in self.tasks
