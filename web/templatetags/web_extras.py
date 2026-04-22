from django import template

register = template.Library()


@register.filter
def lookup(data, key):
    if isinstance(data, dict):
        if key in data:
            return data.get(key)
        str_key = str(key)
        if str_key in data:
            return data.get(str_key)
    return None
