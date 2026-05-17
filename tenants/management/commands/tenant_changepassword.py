from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from django_tenants.utils import schema_context
from tenants.models import Tenant
from getpass import getpass


class Command(BaseCommand):
    help = "Change a user's password inside a specific tenant schema"

    def add_arguments(self, parser):
        parser.add_argument('schema_name', help='Tenant schema name')
        parser.add_argument('username', help='Username in that tenant schema')
        parser.add_argument('password', nargs='?', default=None, help='New password (omit to prompt)')

    def handle(self, *args, **options):
        schema_name = options['schema_name']
        username = options['username']
        password = options['password']

        try:
            tenant = Tenant.objects.get(schema_name=schema_name)
        except Tenant.DoesNotExist:
            raise CommandError(f"Tenant with schema '{schema_name}' does not exist")

        with schema_context(schema_name):
            UserModel = get_user_model()
            try:
                user = UserModel.objects.get(username=username)
            except UserModel.DoesNotExist:
                raise CommandError(f"User '{username}' does not exist in schema '{schema_name}'")

            if password is None:
                password = getpass(f"New password for '{username}' ({schema_name}): ")
                password2 = getpass("Confirm password: ")
                if password != password2:
                    raise CommandError("Passwords do not match")

            user.set_password(password)
            user.save()

        self.stdout.write(self.style.SUCCESS(
            f"Password changed for '{username}' in schema '{schema_name}'"
        ))
