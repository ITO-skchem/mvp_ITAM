from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Create default RBAC groups and permissions"

    def handle(self, *args, **kwargs):
        admin_group, _ = Group.objects.get_or_create(name="admin")
        manager_group, _ = Group.objects.get_or_create(name="manager")
        viewer_group, _ = Group.objects.get_or_create(name="viewer")

        all_perms = Permission.objects.all()
        admin_group.permissions.set(all_perms)

        excluded_models = {"logentry"}
        manager_perms = [perm for perm in all_perms if perm.content_type.model not in excluded_models]
        manager_group.permissions.set(manager_perms)

        viewer_perms = [perm for perm in all_perms if perm.codename.startswith("view_")]
        viewer_group.permissions.set(viewer_perms)

        self.stdout.write(self.style.SUCCESS("RBAC groups created/updated"))
