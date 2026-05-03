"""
Python 3.13+ changed copy semantics for some patterns. Django 4.2's
BaseContext.__copy__ used ``copy(super())``, which no longer produces a
copyable instance — admin and any template context copy then raise
AttributeError ('super' object has no attribute 'dicts').

Upstream fixed this in newer Django branches; this mirrors that fix for
4.2.x until the project upgrades Django.
"""
from __future__ import annotations

import sys


def apply_django_template_context_copy_fix() -> None:
    if sys.version_info < (3, 13):
        return
    from copy import copy as copy_obj

    from django.template import context as template_context

    def basecontext_copy(self):
        duplicate = template_context.BaseContext()
        duplicate.__class__ = self.__class__
        duplicate.__dict__ = copy_obj(self.__dict__)
        duplicate.dicts = self.dicts[:]
        return duplicate

    template_context.BaseContext.__copy__ = basecontext_copy  # type: ignore[method-assign]
