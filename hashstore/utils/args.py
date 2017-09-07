from collections import namedtuple
import argparse
import inspect

getargspec = inspect.getargspec if bytes == str else inspect.getfullargspec

_Opt = namedtuple("_Opt", 'name help default type choices'.split())

Cmd = namedtuple("Cmd", 'name help options'.split())


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
            opt_names, _, _, opt_defaults = getargspec(fn)[:4]
            if opt_names is None:
                opt_names = []
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
                if isinstance(opt_help,tuple):
                    opt_type = opt_help[1]
                    opt_help = opt_help[0]
                if opt_type == Switch:
                    default = False
                    sw = True
                if i >= def_offset:
                    default = opt_defaults[i - def_offset]
                if sw:
                    options.append(Switch(n, opt_help, default))
                else:
                    options.append(Opt(n, opt_help, default, opt_type ))
            self.commands.append(Cmd(fn.__name__, command_help, options))
            return fn
        return decorate

    def get_parser(self, args=None, namespace=None):
        parser = argparse.ArgumentParser(description=self.app_help)
        global_cmd = [c for c in self.commands if c.name == '__init__']
        if len(global_cmd) == 1:
            self.global_opts = global_cmd[0].options
        for opt in self.global_opts:
            opt.add_itself(parser)
        subparsers = parser.add_subparsers()
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

        return parser

    def parse_args(self, args=None, namespace=None):
        return self.get_parser().parse_args(args, namespace)

    def main(self):
        args = self.parse_args()
        def extract_values(opts):
            return {o.name : getattr(args, o.name) for o in opts}
        constructor_args=extract_values(self.global_opts)
        instance = self.app_cls(**constructor_args)
        for c in self.commands:
            if args.command == c.name:
                run_args = extract_values(c.options)
                getattr(instance, c.name)(**run_args)

