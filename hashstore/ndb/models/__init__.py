from hashstore.ndb.models import incoming, shard, glue, server_config, \
    client_config, scan

MODELS = (glue, incoming, client_config, server_config, shard, scan)