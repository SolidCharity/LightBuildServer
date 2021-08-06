from django import template
from django.template.exceptions import TemplateSyntaxError
from toolbox.utils import decode_token

register = template.Library()

class Counter:
    def __init__(self, start, step):
        self.start = start
        self.step = step
        self.value = start
    def __str__(self):
        return str(self.value)
    def reset(self):
        self.value = self.start
        return self
    def inc(self):
        self.value += self.step
        return self
    def dec(self):
        self.value -= self.step
        return self


class CounterNode(template.Node):
    def __init__(self, variable, start, step, reset, inc, dec) -> str:
        self.variable = variable
        self.start = start
        self.step = step
        self.reset = reset
        self.inc = inc
        self.dec = dec
    def render(self, context):
        if not self.variable in context:
            context[self.variable] = Counter(self.start or 0, self.step or 1)
        if self.reset:
            context[self.variable].reset()
        if self.inc:
            context[self.variable].value += self.step or context[self.variable].step
        if self.dec:
            context[self.variable].value -= self.step or context[self.variable].step
        if not (self.inc or self.dec or self.reset):
            value = context[self.variable].value
            context[self.variable].reset()
            context[self.variable].value = value
        return ""

def counter(parser, token):
    _, (variable,), kwargs = decode_token(
        token,
        [
            {"check_identifier": True},
        ],
        {
            "start": {"optional": True, "converter": int},
            "step": {"optional": True, "converter": int},
            "inc": {"is_boolean_arg": True},
            "dec": {"is_boolean_arg": True},
            "reset": {"is_boolean_arg": True},
        },
        allow_unknown_positional_args=False,
        allow_unknown_named_args=False
    )
    return CounterNode(variable=variable, start=kwargs["start"], step=kwargs["step"],
        reset=kwargs["reset"], inc=kwargs["inc"], dec=kwargs["dec"])

register.tag("counter", counter)


class EndCounterNode(template.Node):
    def __init__(self, variable):
        self.variable = variable
    def render(self, context):
        if not self.variable in context:
            raise TemplateSyntaxError(f"Counter {self.variable} does not exist: Expected {{% counter {self.variable} %}} before.")
        del context[self.variable]
        return ""

def endcounter(parser, token):
    _, (variable,), kwargs = decode_token(
        token,
        [
            {"check_identifier": True},
        ],
        {},
        allow_unknown_positional_args=False,
        allow_unknown_named_args=False
    )
    return EndCounterNode(variable=variable)

register.tag("endcounter", endcounter)
