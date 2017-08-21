from collections import Mapping, namedtuple
import argparse

_Opt = namedtuple("_Opt", 'name help default type choices'.split())


class Opt(_Opt):
    def __new__(cls, name, help='', default=None, type=None, choices=None):
        if default is not None:
            help += 'Default is: %r. ' % default
        if choices is not None:
            help += 'Choices are: %r. ' % (choices,)
        return _Opt.__new__(cls, name, help, default, type, choices)

    def add_itself(self, parser):
        parser.add_argument('--%s' % self.name,
                            metavar=self.name, help=self.help,
                            dest=self.name, type=self.type,
                            default=self.default,
                            choices=self.choices)


class Switch(_Opt):
    def __new__(cls, name, help='', default=False):
        return _Opt.__new__(cls, name, help, default, bool, None)

    def add_itself(self, parser):
        parser.set_defaults(**{ self.name : self.default})
        action = 'store_false' if self.default else 'store_true'
        parser.set_defaults(debug=False)
        parser.add_argument('--%s' % self.name,
                            dest=self.name,
                            action=action,
                            help=self.help)


_SPECIAL = ('', '*')


class CliArgs:
    def __init__(self, description, command_definitions):
        def_opts = command_definitions.get('*', [])
        global_opts = command_definitions.get('', [])
        commands = {c: list(def_opts) for c in command_definitions
                    if c not in _SPECIAL}
        for c in commands:
            commands[c].extend(command_definitions[c])

        self.parser = argparse.ArgumentParser(description=description)

        for opt in global_opts:
            opt.add_itself(self.parser)

        subparsers = self.parser.add_subparsers()
        for c in commands:
            opts = commands[c]
            help = None
            command = c
            split = c.split(' - ', maxsplit=2)
            if len(split) > 1:
                command = split[0]
                help = split[1]
            subparser = subparsers.add_parser(command,help=help)
            subparser.description = help
            subparser.set_defaults(command=command)
            for opt in opts:
                opt.add_itself(subparser)

    def parse_args(self, args=None, namespace=None):
        return self.parser.parse_args(args, namespace)