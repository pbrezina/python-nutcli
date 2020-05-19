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
        taskarg=True,
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
        :param taskarg: If True, the first argument of task's handler will be
            the task itself, defaults to True
        :type taskarg: bool, optional
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
        self.taskarg = taskarg
        self.enabled = enabled
        self.timeout = timeout

        self.handler = None
        self.args = []
        self.kwargs = {}

        self.__root_logger = logger if logger is not None else nutcli.message
        self.__logger = None
        self.__parent = None

    def _set_parent(self, parent):
        self.__logger = parent if parent is not None else self.__root_logger
        self.__parent = parent

    def _log_message(self, fn, msg, args, kwargs):
        if self.__parent is not None:
            msg = f'  {msg}'

        fn(msg, *args, **kwargs)

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

        real_args = [self] + self.args if self.taskarg else self.args
        self.__real_handler(kwargs)(*real_args, **self.kwargs)

    def __call__(self, function, *args, **kwargs):
        """
        Setup a function that will be executed by :func:`execute`.

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
            Task('Task 2', taskarg=False)(raise_task),
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
        timeout=None,
        logger=None
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
        :param timeout: Timeout in seconds or specific format (see
            :class:`nutcli.decorators.Timeout`), defaults to None
        :type timeout: int or str, optional
        :param logger: Logger, defaults to (= :class:`nutcli.message`)
        :type logger: logger, optional
        """
        super().__init__(
            name, ignore_errors, always, False, True, timeout, logger
        )
        super().__call__(self._run_tasks)

        self.tag = tag
        self.tasks = []

    def _log_message(self, fn, msg, args, kwargs):
        if self.tag is not None:
            msg = f'[{self.tag}] {msg}'

        super()._log_message(fn, msg, args, kwargs)

    def _run_tasks(self):
        error = None
        for idx, task in enumerate(self.tasks, start=1):
            msg = f'[{idx}/{len(self.tasks)}] {task.name}'

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
            except Exception as e:
                msg = Colorize.all(f'ERROR {e.__class__.__name__}', colorama.Fore.RED)
                self.error(f'{msg}: {str(e)}')
                error = e

        if error is not None:
            raise error

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
