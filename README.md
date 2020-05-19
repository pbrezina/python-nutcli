# nutcli - cli in a nutshell

The Python ``nutcli`` package allows you to easily create robust command-based
command line interface that can combine the best of the two worlds of
``python`` and ``shell``.

It also provides several useful classes and decorators that can help you improve
the user experience by producing nicely formatted output and allowing dry runs
for operations with side effects.

## Links

* Project source code: https://github.com/pbrezina/python-nutcli
* Project documentation: https://nutcli.readthedocs.io
* Project at PyPi: https://pypi.org/project/nutcli

## Installation

```
pip3 install nutcli
```

## Example instead of thousands words

Bellow is the very basic example to get the idea of what this package does and
how its used.

```python
class HelloActor(Actor):
    def setup_parser(self, parser):
        parser.add_argument('--hello', action='store', type=str)

    def __call__(self, hello):
        self.info(hello)
        return 0

class Program:
    def main(self, argv):
        # Create argument parser.
        parser = argparse.ArgumentParser()

        CommandParser('Example Commands')([
            Command('hello', 'Print hello message', HelloActor()),
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
```

```console
$ python3 ./main.py hello --hello world
[my-cli] world
$ python3 ./main.py --help
usage: main.py [-h] [--log-execution] [--dry-run] [--no-colors] COMMANDS ...

optional arguments:
-h, --help       show this help message and exit
--log-execution  Log execution of operations that supports it.
--dry-run        Do not execute operations with side effects. Only log what
                    would be done.
--no-colors      Do not execute operations with side effects. Only log what
                    would be done.

Example Commands:
COMMANDS
    hello          Print hello message
```