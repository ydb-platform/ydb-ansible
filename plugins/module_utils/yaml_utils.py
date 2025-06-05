import yaml
try:
    from yaml import CSafeDumper as SafeDumper
except ImportError:
    from yaml import SafeDumper


class CustomYAMLDumper(SafeDumper):
    """
    Custom YAML Dumper that preserves !inherit tags.
    """
    pass


# Custom YAML tag handler for !inherit during loading
class InheritableDict(dict):
    """A dict subclass that can hold a YAML tag."""
    tag = None


def inherit_constructor(loader, node):
    """
    Constructor for !inherit tags.
    When a node has the !inherit tag, creates an InheritableDict with the tag set.
    """
    value = loader.construct_mapping(node) if isinstance(node, yaml.MappingNode) else {}
    result = InheritableDict(value)
    result.tag = '!inherit'
    return result


# Create a custom Loader class that knows about !inherit
class CustomYAMLLoader(yaml.SafeLoader):
    """
    Custom YAML Loader that preserves !inherit tags.
    """
    pass


# Register the constructor for !inherit tags
CustomYAMLLoader.add_constructor('!inherit', inherit_constructor)


def represent_undefined(dumper, data):
    """
    Custom representer for handling !inherit tags.
    When data is '!inherit', preserves it as a YAML tag.
    Otherwise, represents it as a regular string.
    """
    if data == '!inherit':
        return dumper.represent_scalar('!inherit', '')
    return dumper.represent_scalar('tag:yaml.org,2002:str', str(data))


def represent_none(dumper, data):
    """
    Custom representer for None values.
    Represents None as null in YAML.
    """
    return dumper.represent_scalar('tag:yaml.org,2002:null', 'null')


# Add a representer for InheritableDict
def represent_inheritable_dict(dumper, data):
    """
    Represent an InheritableDict in YAML with its tag.
    """
    return dumper.represent_mapping(data.tag if data.tag else 'tag:yaml.org,2002:map', data)


# Register custom representers
CustomYAMLDumper.add_representer(type(None), represent_none)
CustomYAMLDumper.add_representer(InheritableDict, represent_inheritable_dict)


def safe_dump(data, file_obj, **kwargs):
    """
    Safely dump YAML data to a file while preserving !inherit tags.

    Args:
        data: The data to dump
        file_obj: A file-like object to dump to
        **kwargs: Additional arguments to pass to yaml.dump
    """
    kwargs.setdefault('Dumper', CustomYAMLDumper)
    kwargs.setdefault('default_flow_style', False)
    return yaml.dump(data, file_obj, **kwargs)


def safe_load(stream):
    """
    Safely load YAML data from a stream while preserving !inherit tags.

    Args:
        stream: A string or file-like object to load from

    Returns:
        The loaded YAML data
    """
    return yaml.load(stream, Loader=CustomYAMLLoader)