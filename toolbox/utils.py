from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional, Tuple
from numbers import Number
from django.template import TemplateSyntaxError
from django.template.base import Token


BOOLEAN_TRUE = ["yes", "true"]
BOOLEAN_FALSE = ["no", "false"]

def to_boolean(
        obj: Any, additional_true=None, additional_false=None,
        empty_string=False, unknown_string=True, unknown_type=True
    ) -> bool:
    """Converts any object to bool.
    
    Rules applied before check:
     1. If obj is a str, whitespaced will be stripped off (see str.strip()) and it will be converted to lowercase (see str.lower()).
     2. If obj is a numeric str (see str.isnumeric()), it will be converted to a Number.

    Returns True if:
     - obj is a bool and True,
     - obj is a Number and greater than zero,
     - obj is a str and in the BOOLEAN_TRUE (module constant) or additional_true (argument),
     - obj is an empty string and empty_string (argument) is True,
     - obj is an unknown string and unknown_string (argument) is True,
     - obj is an unknown type (not None, bool, numbers.Number or str) and unknown_type (argument) is True
    
    Returns False if:
     - obj is a bool and False,
     - obj is a Number and not greater than zero,
     - obj is a str and in the BOOLEAN_FALSE (module constant) or additional_false (argument),
     - obj is an empty string and empty_string (argument) is False,
     - obj is an unknown string and unknown_string (argument) is False,
     - obj is an unknown type (not None, bool, numbers.Number or str) and unknown_type (argument) is False
    """
    if obj is None:
        return False
    if isinstance(obj, bool):
        return obj
    elif isinstance(obj, Number):
        return obj > 0
    elif isinstance(obj, str):
        obj = obj.strip().lower()
        if obj.isnumeric():
            return float(obj) > 0
        elif obj in BOOLEAN_TRUE or obj in additional_true:
            return True
        elif obj in BOOLEAN_FALSE or obj in additional_false:
            return False
        elif obj == "":
            return empty_string
        else:
            return unknown_string
    else:
        return unknown_type

def split_named_argument(arg: str) -> Tuple[Optional[str], str]:
    """Splits an argument at '='. Returns (name, value) if named, or (value,) if without name."""
    return arg.split("=", 1)

def decode_token(
        token: Token, positional_args: Iterable[Mapping[str, Any]], named_args: Mapping[str, Mapping[str, Any]],
        allow_unknown_positional_args: bool, allow_unknown_named_args: bool
    ) -> Tuple[List[Any], Dict[str, Any]]:
    """Splits the token and returns its name and positional as well as named arguments.

    positional_args is a sequence of option sets specifying expected positional args.
    named_args assigns each argument name a set of options specifying expected named args.

    options:
    quotes [str]: option to control quote handling: "disallowed", "optional", "required", "ignore" (all besides "ignore" cut off quotes if they match) [default: "optional"]
    converter [Callable]: Callable used to convert the string argument into another type; if None, converter will not be called [default: None]
    optional [bool]: option specifying whether the argument is optional [default: False]
    default [Any]: default value to return if argument is not given explicitly (if Callable: return value of Callable will be used) [default: None]
    check_identifier [bool]: if True check whether the argument value is a valid python identifier with str.isidentifier() [default: False]
    is_boolean_arg [bool]: if True the argument is treated as Boolean-Argument -> see Boolean-Args below (named_args only) [default: False]

    Boolean-Args:
    Boolean-Args are named arguments which can look like positional ones. But their presence is treated like True and absence like False.
    However assignments (normal named argument notation) are always possible too (-> converted will be utils.to_bool()).
    Example:
        {% my_tag silent=True %} is the same as {% my_tag silent %}
        {% my_tag silent=False %} is the same as {% my_tag %}
    """
    # default values for options
    DEFAULT_QUOTES = "optional"
    DEFAULT_CONVERTER = None
    DEFAULT_OPTIONAL = False
    DEFAULT_DEFAULT = None
    DEFAULT_CHECK_IDENTIFIER = False
    DEFAULT_IS_BOOLEAN_ARG = False

    # sort positional and named args
    tag_name, *contents = token.split_contents()
    positional = []
    named = {}
    positional_res = []
    named_res = {}
    for i, content in enumerate(contents):
        arg = split_named_argument(content)
        if len(arg) == 1:
            if len(named) > 0:
                raise TemplateSyntaxError(f"Named argument ({list(named.keys())[-1]}) must not be followed by positional argument.")
            positional.append(arg[0])
        else:
            named[arg[0]] = arg[1]

    # do positional args
    positional_iter = iter(positional)
    i = 0
    for options in positional_args:
        try:
            arg = next(positional_iter)
        except StopIteration:
            if options.get("optional", DEFAULT_OPTIONAL):
                positional_res.append(options["default"]() if isinstance(options.get("default", DEFAULT_DEFAULT), Callable) else options.get("default", DEFAULT_DEFAULT))
            else:
                raise TemplateSyntaxError(f"Positional argument {i} is not optional.")
        else:
            if arg[0] == arg[-1] and arg[0] in ("'", '"'):
                if options.get("quotes", DEFAULT_QUOTES) == "disallowed":
                    raise TemplateSyntaxError(f"Positional argument {i} must not be inside quotes.")
                elif options.get("quotes", DEFAULT_QUOTES) == "optional":
                    arg = arg[1:-1]
                elif options.get("quotes", DEFAULT_QUOTES) == "required":
                    arg = arg[1:-1]
            else:
                if options.get("quotes", DEFAULT_QUOTES) == "required":
                    raise TemplateSyntaxError(f"Positional argument {i} must be inside quotes.")
            if options.get("check_identifier", DEFAULT_CHECK_IDENTIFIER) and not arg.isidentifier():
                raise TemplateSyntaxError(f"Positional argument {i} must be a valid python identifier.")
            positional_res.append(arg if options.get("quotes", DEFAULT_CONVERTER) is None else options["converter"](arg))
        i += 1
    remaining = list(positional_iter)
    for arg in remaining:
        if not allow_unknown_positional_args and len(remaining) > 0:
            if arg in named_args and named_args[arg].get("is_boolean_arg", DEFAULT_IS_BOOLEAN_ARG): # handle Boolean-Arg (positional notation)
                named_res[arg] = True
            else:
                raise TemplateSyntaxError(f"Positional argument {i} is not allowed.")
        else:
            if arg in named_args and named_args[arg].get("is_boolean_arg", DEFAULT_IS_BOOLEAN_ARG): # handle Boolean-Arg (positional notation)
                named_res[arg] = True
            else:
                positional_res.append(arg)

    # do named args
    for argname, options in named_args.items():
        arg: Any
        if argname in named_res and not options["is_boolean_arg"]:
            raise TemplateSyntaxError(f"Named argument {argname} can only be given once.")
        elif options.get("is_boolean_arg", DEFAULT_IS_BOOLEAN_ARG): # handle Boolean-Arg (assignment notation)
            if argname in named:
                arg = named[argname]
                if arg[0] == arg[-1] and arg[0] in ("'", '"'):
                    arg = arg[1:-1]
                named_res[argname] = to_boolean(arg)
            elif not argname in named_res:
                named_res[argname] = False
        elif argname in named:
            arg = named[argname]
            if arg[0] == arg[-1] and arg[0] in ("'", '"'):
                if options.get("quotes", DEFAULT_QUOTES) == "disallowed":
                    raise TemplateSyntaxError(f"Named argument {argname} must not be inside quotes.")
                elif options.get("quotes", DEFAULT_QUOTES) == "optional":
                    arg = arg[1:-1]
                elif options.get("quotes", DEFAULT_QUOTES) == "required":
                    arg = arg[1:-1]
            else:
                if options.get("quotes", DEFAULT_QUOTES) == "required":
                    raise TemplateSyntaxError(f"Named argument {argname} must be inside quotes.")
            if options.get("check_identifier", DEFAULT_CHECK_IDENTIFIER) and not arg.isidentifier():
                raise TemplateSyntaxError(f"Positional argument {i} must be a valid python identifier.")
            named_res[argname] = arg if options.get("converter", DEFAULT_CONVERTER) is None else options["converter"](arg)
        elif options.get("optional", DEFAULT_OPTIONAL):
            named_res[argname] = options["default"]() if isinstance(options.get("default", DEFAULT_DEFAULT), Callable) else options.get("default", DEFAULT_DEFAULT)
        else:
            raise TemplateSyntaxError(f"Named argument {argname} is not optional.")
        if argname in named:
            del named[argname]
    if not allow_unknown_named_args and len(named) > 0:
        raise TemplateSyntaxError(f"Named argument {next(iter(named.keys()))} is not allowed.")
    else:
        named_res.update(named)
    
    # return result
    return tag_name, positional_res, named_res
