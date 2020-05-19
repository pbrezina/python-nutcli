Example Usage
=============

Below are several examples of most useful features. You can just take and edit
those to code your command line interface.

.. contents::

Example 1: Setting up commands, command groups and nesting commands
-------------------------------------------------------------------

In the single example code below are shown all possible use cases on how
to combined different command parser to create your interface.

Just switch ``Actor()`` with an instance of your own class that inherits
from ``Actor`` and you are good to go.

.. code-block:: python

   class Program:
      def main(self, argv):
         # Create argument parser.
         parser = argparse.ArgumentParser()

         CommandParser('Example Commands')([
               Command('example-1', 'First level command', Actor()),
               CommandGroup('Grouped commands')([
                  Command('example-2-A', 'Grouped command', Actor()),
                  Command('example-2-B', 'Grouped command', Actor()),
               ]),
               Command('nested', 'Commands can be nested',
                  CommandParser('Nested commands')([
                     Command('example-3', 'Second level command', Actor()),
                  ])
               ),
               [
                  Command('example-4', 'You can include another list', Actor()),
               ]
         ]).setup_parser(parser)

         # Create the runner object.
         runner = Runner('my-cli', parser).setup_parser()

         # Parse arguments - the runner internally process its own arguments
         # that were setup by previous call to `setup_parser()`.
         args = runner.parse_args(argv)

         # You can handle your own global arguments here.

         # Now we setup the default logger - it produces output to stdout
         # and stderr.
         runner.default_logger()

         # And finally, we execute the requested command and return its exit
         # code.
         return runner.execute(args)


   if __name__ == "__main__":
      program = Program()
      sys.exit(program.main(sys.argv[1:]))

.. code-block:: console

   $ python3 ./main.py  --help
   usage: main.py [-h] [--log-execution] [--dry-run] [--no-colors] COMMANDS ...

   optional arguments:
   -h, --help        show this help message and exit
   --log-execution   Log execution of operations that supports it.
   --dry-run         Do not execute operations with side effects. Only log what
                     would be done.
   --no-colors       Do not execute operations with side effects. Only log what
                     would be done.

   Example Commands:
   COMMANDS
      example-1       First level command
      Grouped commands
         example-2-A   Grouped command
         example-2-B   Grouped command
      nested          Commands can be nested
      example-4       You can include another list


Example 2: Accessing shell from custom Actor
--------------------------------------------

.. code-block:: python

   class ExampleActor(Actor):
      def __call__(self):
         self.info('The following command will produce hello world message')
         self.shell('echo "hello world"')

.. code-block:: console

   $ python3 ./main.py example-actor
   [my-cli] The following command will produce hello world message
   hello world

Example 3: Shell command must return non-zero status code by default
--------------------------------------------------------------------

.. code-block:: python

   class ExampleActor(Actor):
      def __call__(self):
         self.shell('exit 1')

.. code-block:: console

   $ python3 ./main.py example-actor
   [my-cli] The following command will produce hello world message
   [my-cli] The following command exited with: 1
   [my-cli] [shell] Working directory: /home/pbrezina/workspace/python-nutcli
   [my-cli] [shell] Environment:
   [my-cli] [shell] Command: exit 1
   Traceback (most recent call last):
   File "/home/pbrezina/workspace/python-nutcli/nutcli/runner.py", line 210, in execute
      return self._call_actor(args.func, args, shell)
   File "/home/pbrezina/workspace/python-nutcli/nutcli/runner.py", line 249, in _call_actor
      return actor(**actor._filter_parser_args(args))
   File "./main.py", line 21, in __call__
      self.shell('exit 1')
   File "/home/pbrezina/workspace/python-nutcli/nutcli/shell.py", line 197, in __call__
      ) from None
   nutcli.shell.ShellCommandError: Command returned non-zero status code: 1

Example 4: Shell commands can be dry-run by default
---------------------------------------------------

.. code-block:: python

   class ExampleActor(Actor):
      def __call__(self):
         self.shell('exit 1')

.. code-block:: console

   $ python3 ./main.py --dry-run example-actor
   [my-cli] [shell] Working directory: /home/pbrezina/workspace/python-nutcli
   [my-cli] [shell] Environment:
   [my-cli] [shell] Command: exit 1

Example 5: You can use a TaskList
---------------------------------

.. code-block:: python

   class ExampleActor(Actor):
      def __call__(self):
         tasklist = TaskList('my-tasks')([
               Task('Task 1')(lambda task: task.info('Hello')),
               Task('Task 2')(lambda task: task.info('World')),
         ])

         tasklist.execute()

.. code-block:: console

   $ python3 ./main.py example-actor
   [my-cli] [my-tasks] [1/2] Task 1
   [my-cli] [my-tasks]   Hello
   [my-cli] [my-tasks] [2/2] Task 2
   [my-cli] [my-tasks]   World

Example 6: Tasks can be nested
------------------------------

.. code-block:: python

   class ExampleActor(Actor):
      def __call__(self):
        tasklist = TaskList('my-tasks')([
            Task('Task 1')(lambda task: task.info('Hello')),
            Task('Task 2')(lambda task: task.info('World')),
            TaskList()([
                Task('Task 3')(lambda task: task.info('Nested 1')),
                Task('Task 4')(lambda task: task.info('Nested 2')),
            ])
        ])

        tasklist.execute()

.. code-block:: console

   $ python3 ./main.py example-actor
   [my-cli] [my-tasks] [1/3] Task 1
   [my-cli] [my-tasks]   Hello
   [my-cli] [my-tasks] [2/3] Task 2
   [my-cli] [my-tasks]   World
   [my-cli] [my-tasks] [3/3]
   [my-cli] [my-tasks]   [1/2] Task 3
   [my-cli] [my-tasks]     Nested 1
   [my-cli] [my-tasks]   [2/2] Task 4
   [my-cli] [my-tasks]     Nested 2

Example 7: Tasks can have finalizers
------------------------------------

.. code-block:: python

   class ExampleActor(Actor):
      def __call__(self):
        def raise_error(task, msg):
            raise Exception(msg)

        tasklist = TaskList('my-tasks')([
            Task('Task 1')(lambda task: task.info('Hello')),
            Task('Task 2')(raise_error, 'Ooops.'),
            Task('Task 3')(lambda task: task.info('Skipped.')),
            Task.Cleanup('Task 4')(lambda task: task.info('Cleanup.')),
        ])

        tasklist.execute()

.. code-block:: console

   $ python3 ./main.py example-actor
   [my-cli] [my-tasks] [1/4] Task 1
   [my-cli] [my-tasks]   Hello
   [my-cli] [my-tasks] [2/4] Task 2
   [my-cli] [my-tasks] ERROR Exception: Ooops.
   [my-cli] [my-tasks] [3/4] Task 3 (skipped on error)
   [my-cli] [my-tasks] [4/4] Task 4 (finalizing)
   [my-cli] [my-tasks]   Cleanup.
   [my-cli] Exception Exception: Ooops.
   Traceback (most recent call last):
   File "/home/pbrezina/workspace/python-nutcli/nutcli/runner.py", line 210, in execute
      return self._call_actor(args.func, args, shell)
   File "/home/pbrezina/workspace/python-nutcli/nutcli/runner.py", line 249, in _call_actor
      return actor(**actor._filter_parser_args(args))
   File "./main.py", line 30, in __call__
      tasklist.execute()
   File "/home/pbrezina/workspace/python-nutcli/nutcli/tasks.py", line 157, in execute
      self.__real_handler(kwargs)(*real_args, **self.kwargs)
   File "/home/pbrezina/workspace/python-nutcli/nutcli/tasks.py", line 336, in _run_tasks
      raise error
   File "/home/pbrezina/workspace/python-nutcli/nutcli/tasks.py", line 329, in _run_tasks
      task.execute(parent=self)
   File "/home/pbrezina/workspace/python-nutcli/nutcli/tasks.py", line 157, in execute
      self.__real_handler(kwargs)(*real_args, **self.kwargs)
   File "./main.py", line 21, in raise_error
      raise Exception(msg)
   Exception: Ooops.
