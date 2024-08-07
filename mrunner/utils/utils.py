import logging
import re
from collections import OrderedDict, namedtuple
from tempfile import NamedTemporaryFile

import attr
import attrs
import six
from jinja2 import Environment, PackageLoader, StrictUndefined
from path import Path

from mrunner.backends import get_context_cls

LOGGER = logging.getLogger(__name__)


def pathify(path, separator="-"):
    return re.sub(r"[ ]+", separator, path.lower())


def parse_argv(parser, argv):
    try:
        divider_pos = argv.index("--")
        mrunner_argv = argv[1:divider_pos]
        rest_argv = argv[divider_pos + 1 :]
    except ValueError:
        # when missing '--' separator
        mrunner_argv = argv
        rest_argv = []
    return parser.parse_args(args=mrunner_argv), rest_argv


template_env = Environment(
    loader=PackageLoader("mrunner", "templates"), undefined=StrictUndefined
)


class TempFile(object):

    def __init__(self, dir=None):
        self._file = NamedTemporaryFile(prefix="mrunner_", dir=dir)

    def write(self, payload):
        self._file.write(payload)
        self._file.flush()

    @property
    def path(self):
        return Path(self._file.name)


class GeneratedTemplateFile(TempFile):

    def __init__(self, template_filename=None, **kwargs):
        super(GeneratedTemplateFile, self).__init__()
        template = template_env.get_template(template_filename)
        payload = template.render(**kwargs).encode(encoding="utf-8")
        self.write(payload)


PathToDump = namedtuple("PathToDump", "local_path rel_remote_path")


@attr.s
class WrapperCmd(object):

    _cmd = attr.ib()
    _experiment_config_path = attr.ib()

    @property
    def command(self):
        cmd = (
            self._cmd.split(" ")
            if isinstance(self._cmd, six.string_types)
            else self._cmd
        )
        config_argv = ["--config", "config_$SLURM_ARRAY_TASK_ID"]
        cmd = cmd + config_argv
        return " ".join(cmd)


def get_paths_to_copy(paths_to_copy=None, exclude=None):
    """Lists paths to copy from current working directory, after excluding paths from exclude list;
    additionally paths_to_copy are copied"""

    if paths_to_copy is None:
        paths_to_copy = []
    if exclude is None:
        exclude = [".git", ".gitignore", ".gitmodules"]
    exclude = [Path(e).abspath() for e in exclude]

    def _list_dir(d):
        directories = []
        for p in Path(d).listdir():
            p = p.abspath()
            excluded = False
            for e in exclude:
                e = Path(e).abspath()
                if not e.relpath(p).startswith(".."):
                    excluded = True
                    # if excluded subdir - not whole current
                    if e != p:
                        directories += _list_dir(p)
                    break
            if not excluded:
                directories.append(PathToDump(p.relpath("."), p.relpath(".")))
        return directories

    result = _list_dir(Path("."))
    for external in paths_to_copy:
        if ":" in external:
            src, rel_dst = external.split(":")
        else:
            src = external
            # get relative to cwd split into items on each '/' and remove relative parts
            rel_dst = "/".join(
                [
                    item
                    for item in Path(external).relpath(".").splitall()
                    if item and item != ".."
                ]
            )
        result.append(PathToDump(Path(src).relpath("."), Path(rel_dst).relpath(".")))

    result = set(result)
    LOGGER.debug(
        "get_paths_to_copy(paths_to_copy=%s, exclude=%s) result=%s",
        str(paths_to_copy),
        str(exclude),
        str([str(s) for s, d in result]),
    )
    return result


def make_attr_class(class_name, fields, **class_kwargs):
    fields = OrderedDict(
        [
            (k, attr.ib(**kwargs) if isinstance(kwargs, dict) else kwargs)
            for k, kwargs in fields
        ]
    )
    return attr.make_class(class_name, fields, **class_kwargs)


def filter_only_attr(AttrClass, d):
    available_fields = [f.name for f in attr.fields(AttrClass)]
    for k, v in d.items():
        if k in available_fields:
            continue
        LOGGER.debug("Ignoring argument %s=%s", str(k), str(v))
    return {k: v for k, v in d.items() if k in available_fields}


def validate_context(context_dict: dict):
    """This function checks:
    1. weather all required parameters of the context are present in the context_dict
    2. weather all keys in the context_dict have corresponding fields in the context
        class
    """
    if "backend_type" not in context_dict:
        raise AttributeError(
            f"Context `{context_dict['context_name']}` is missing required field `backend_type`."
        )

    context_cls = get_context_cls(context_dict["backend_type"])

    required_params = {
        f.name
        for f in attrs.fields(context_cls)
        if f.default == attrs.NOTHING and f.init is True
    }
    params = {f.name for f in attrs.fields(context_cls) if f.init is True}

    for p in required_params:
        if p not in context_dict:
            raise ValueError(
                f"In context {context_dict['context_name']}: backend {context_dict['backend_type']} requires field `{p}`."
            )

    for p in context_dict:
        if p not in params:
            raise ValueError(
                f"Parameter `{p}` is not supported by the backend {context_dict['backend_type']}. Please fix context {context_dict['context_name']}."
            )
