from django import template

register = template.Library()

@register.filter
def sum_values(value):
    """
    Фильтр суммирует значения в списке или словаре.
    """
    if isinstance(value, dict):
        return sum(value.values())
    elif isinstance(value, (list, tuple)):
        return sum(value)
    return 0


@register.filter
def sum_teachers_values(value_list):
    return sum([item['value'] for item in value_list])
