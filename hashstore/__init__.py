import pkg_resources

plugins = [
    (entry_point.name, entry_point.load())
    for entry_point in pkg_resources.iter_entry_points('hashstore.plugins')
]


