from core.models import Code


def get_code_choices(group_key, include_blank=True, current_value=None):
    choices = []
    if include_blank:
        choices.append(("", "---------"))

    code_rows = Code.objects.filter(group__key=group_key, group__is_active=True, is_active=True).select_related("group")
    code_rows = code_rows.order_by("group__sort_order", "sort_order", "code")
    choices.extend([(row.code, row.name) for row in code_rows])

    if current_value and current_value not in {code for code, _ in choices}:
        choices.append((current_value, f"{current_value} (미등록 코드)"))

    return choices
