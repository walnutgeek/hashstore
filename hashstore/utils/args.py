from collections import namedtuple
import argparse
from inspect import getfullargspec



_Opt = namedtuple("_Opt", ['name', 'help', 'has_default', 'default',
                           'type', 'choices'])

Cmd = namedtuple("Cmd", ['name', 'help', 'options'])


class Opt(_Opt):
    def __new__(cls, name, help='', has_default=False, default=None, type=None, choices=None):
        if has_default:
            help += 'Default is: %r. ' % default
        if choices is not None:
            help += 'Choices are: %r. ' % ([str(s) for s in choices],)
        return _Opt.__new__(cls, name, help, has_default, default, type, choices)

    def add_itself(self, parser):
        parser.add_argument('--%s' % self.name,
                            metavar=self.name, help=self.help,
                            dest=self.name, type=self.type,
                            required=not(self.has_default),
                            default=self.default,
                            choices=self.choices)


class Switch(_Opt):
    def __new__(cls, name, help='', default=False):
        return _Opt.__new__(cls, name, help, True, default, bool, None)

    def add_itself(self, parser):
        parser.set_defaults(**{ self.name : self.default})
        action = 'store_false' if self.default else 'store_true'
        parser.set_defaults(debug=False)
        parser.add_argument('--%s' % self.name,
                            dest=self.name,
                            action=action,
                            help=self.help)


class CommandArgs:
    def __init__(self):
        self.app_help = ''
        self.app_cls = None
        self.commands = []
        self.global_opts = []

    def app(self, app_help):
        self.app_help = app_help
        def decorate(fn):
            self.app_cls = fn
            return fn
        return decorate

    def command(self, command_help='', **opthelp_kw):
        def decorate(fn):
            options = []
            opt_names, _, _, opt_defaults = getfullargspec(fn)[:4]
            if opt_defaults is None:
                opt_defaults = []
            def_offset = len(opt_names) - len(opt_defaults)
            for i, n in enumerate(opt_names):
                if i == 0:
                    continue
                default = None
                sw = False
                opt_type = None
                opt_help = opthelp_kw.get(n, '')
                opt_choices = None
                if isinstance(opt_help,tuple):
                    if len(opt_help) > 2:
                        opt_choices = opt_help[2]
                    opt_type = opt_help[1]
                    opt_help = opt_help[0]
                has_default = True
                if opt_type == Switch:
                    default = False
                    sw = True
                if i >= def_offset:
                    default = opt_defaults[i - def_offset]
                else:
                    has_default = False
                if sw:
                    options.append(Switch(n, opt_help, default))
                else:
                    options.append(Opt(n, opt_help, has_default, default, opt_type, opt_choices ))
            self.commands.append(Cmd(fn.__name__, command_help, options))
            return fn
        return decorate

    def get_parser(self):
        self.parser = argparse.ArgumentParser(description=self.app_help)
        global_cmd = [c for c in self.commands if c.name == '__init__']
        self.parser.set_defaults(command='')
        if len(global_cmd) == 1:
            self.global_opts = global_cmd[0].options
        for opt in self.global_opts:
            opt.add_itself(self.parser)
        subparsers = self.parser.add_subparsers()
        for c in self.commands:
            if c.name == '__init__':
                continue
            opts = c.options
            help = c.help
            subparser = subparsers.add_parser(c.name,help=help)
            subparser.description = help
            subparser.set_defaults(command=c.name)
            for opt in opts:
                opt.add_itself(subparser)

        return self.parser

    def parse_args(self, args=None, namespace=None):
        return self.get_parser().parse_args(args, namespace)

    def main(self):
        self.run(self.parse_args())

    def run(self, args):
        def extract_values(opts):
            return {o.name: getattr(args, o.name) for o in opts}

        constructor_args = extract_values(self.global_opts)
        instance = self.app_cls(**constructor_args)
        for c in self.commands:
            if args.command == c.name:
                run_args = extract_values(c.options)
                getattr(instance, c.name)(**run_args)
                break
        else:
            self.parser.print_help()


