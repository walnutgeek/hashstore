from hashstore.utils import exception_message
from hashstore.utils.args import getargspec


def _identity(x):
    return x


class _NamedMixin:
    def register(self, calls_dict):
        calls_dict[self.name] = self


class ApiCallParam(_NamedMixin):
    def __init__(self, name, doc, default, required, coerce_fn):
        self.name = name
        self.doc = doc
        self.default = default
        self.required = required
        self.coerce_fn = coerce_fn


class ApiCall(_NamedMixin):
    def __init__(self, fn, opt_names, opt_defaults,
                 params_metadata, coerce_return_fn, coerce_error_fn):
        self.name = fn.__name__
        self.doc = fn.__doc__
        self.coerce_return_fn = coerce_return_fn
        self.coerce_error_fn = coerce_error_fn
        self.params = {}
        offset = len(opt_names) - len(opt_defaults)
        for i, param_name in enumerate(opt_names):
            if i == 0:  # ignore `self`
                continue
            meta = params_metadata.get(param_name, _identity)
            coerce_fn, param_doc = meta if isinstance(meta, tuple) \
                else (meta, None)
            required = i < offset
            ApiCallParam(
                param_name,
                param_doc,
                opt_defaults[i - offset] if not required else None,
                required,
                coerce_fn
            ).register(self.params)


class ApiCallRegistry:
    def __init__(self):
        self.calls = {}

    def call(self, coerce_return_fn=_identity,
             coerce_error_fn=_identity, **params_metadata):
        def decorate(fn):
            opt_names, _, _, opt_defaults = getargspec(fn)[:4]
            if opt_defaults is None:
                opt_defaults = []
            ApiCall(fn,
                    opt_names,
                    opt_defaults,
                    params_metadata,
                    coerce_return_fn,
                    coerce_error_fn
                    ).register(self.calls)

            return fn
        return decorate

    def run(self, obj, method_name, params):
        call_meta = self.calls[method_name]
        converted = {}
        required = set(k for k in call_meta.params
                       if call_meta.params[k].required)
        for k in params:
            if k not in call_meta.params:
                raise TypeError('%s() does not have argument: %r' %
                                (method_name, k))
            param_meta = call_meta.params[k]
            converted[k] = param_meta.coerce_fn(params[k])
            required.remove(k)

        if len(required) > 0:
            raise TypeError('%s() is missing required arguments: %r' %
                            (method_name, list(required)))
        try:
            r = getattr(obj, method_name)(**converted)
            return {'result': call_meta.coerce_return_fn(r)}
        except:
            msg = exception_message()
            return {'error': call_meta.coerce_error_fn(msg)}
