import yaml

class SafeUnknownConstructor(yaml.constructor.SafeConstructor):
    def __init__(self):
        yaml.constructor.SafeConstructor.__init__(self)

    def construct_undefined(self, node):
        data = getattr(self, 'construct_' + node.id)(node)
        datatype = type(data)
        wraptype = type('TagWrap_'+datatype.__name__, (datatype,), {})
        wrapdata = wraptype(data)
        wrapdata.tag = lambda: None
        wrapdata.datatype = lambda: None
        setattr(wrapdata, "wrapTag", node.tag)
        setattr(wrapdata, "wrapType", datatype)
        return wrapdata


class SafeUnknownLoader(SafeUnknownConstructor, yaml.loader.SafeLoader):

    def __init__(self, stream):
        SafeUnknownConstructor.__init__(self)
        yaml.loader.SafeLoader.__init__(self, stream)


class SafeUnknownRepresenter(yaml.representer.SafeRepresenter):
    def represent_data(self, wrapdata):
        tag = False
        if type(wrapdata).__name__.startswith('TagWrap_'):
            datatype = getattr(wrapdata, "wrapType")
            tag = getattr(wrapdata, "wrapTag")
            data = datatype(wrapdata)
        else:
            data = wrapdata
        node = super(SafeUnknownRepresenter, self).represent_data(data)
        if tag:
            node.tag = tag
        return node

class SafeUnknownDumper(SafeUnknownRepresenter, yaml.dumper.SafeDumper):

    def __init__(self, stream,
            default_style=None, default_flow_style=False,
            canonical=None, indent=None, width=None,
            allow_unicode=None, line_break=None,
            encoding=None, explicit_start=None, explicit_end=None,
            version=None, tags=None, sort_keys=True):

        SafeUnknownRepresenter.__init__(self, default_style=default_style,
                default_flow_style=default_flow_style, sort_keys=sort_keys)

        yaml.dumper.SafeDumper.__init__(self,  stream,
                                        default_style=default_style,
                                        default_flow_style=default_flow_style,
                                        canonical=canonical,
                                        indent=indent,
                                        width=width,
                                        allow_unicode=allow_unicode,
                                        line_break=line_break,
                                        encoding=encoding,
                                        explicit_start=explicit_start,
                                        explicit_end=explicit_end,
                                        version=version,
                                        tags=tags,
                                        sort_keys=sort_keys)


MySafeLoader = SafeUnknownLoader
yaml.constructor.SafeConstructor.add_constructor(None, SafeUnknownConstructor.construct_undefined)

def yaml_tag(data,tag):
    """
    Add tag to data

    Args:
        data: The data to tag
        tag: tag (!inherit, !remove, ..)
    """
    datatype = type(data)
    wraptype = type('TagWrap_'+datatype.__name__, (datatype,), {})
    wrapdata = wraptype(data)
    wrapdata.tag = lambda: None
    wrapdata.datatype = lambda: None
    setattr(wrapdata, "wrapTag", tag)
    setattr(wrapdata, "wrapType", datatype)
    return wrapdata

def safe_dump(data, file_obj, **kwargs):
    """
    Safely dump YAML data to a file while preserving tags.

    Args:
        data: The data to dump
        file_obj: A file-like object to dump to
        **kwargs: Additional arguments to pass to yaml.dump
    """
    kwargs.setdefault('Dumper', SafeUnknownDumper)
    kwargs.setdefault('default_flow_style', False)
    kwargs.setdefault('allow_unicode', True)
    return yaml.dump(data, file_obj, **kwargs)


def safe_load(stream):
    """
    Safely load YAML data from a stream while preserving tags.

    Args:
        stream: A string or file-like object to load from

    Returns:
        The loaded YAML data
    """
    return yaml.load(stream, Loader=SafeUnknownLoader)