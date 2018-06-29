import pkg_resources
import inspect

plugins = [
    (entry_point.name, entry_point.load())
    for entry_point in pkg_resources.iter_entry_points('hashstore.plugins')
]


modules = { m.__name__ : m for n, m in plugins
            if n == 'module' and inspect.ismodule(m) }

