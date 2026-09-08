"""
Comando de gestión que crea un superusuario a partir de variables de
entorno, pensado para ejecutarse automáticamente en cada despliegue
(ver el 'buildCommand' de render.yaml).

Se usa en vez del 'createsuperuser --noinput' de Django porque ese
comando falla con un error si el usuario ya existe, lo que rompería el
build a partir del segundo despliegue. Este comando es idempotente: si
el usuario ya existe, no hace nada; si no, lo crea. Y si las variables
de entorno no están definidas (por ejemplo, en local), simplemente no
hace nada, sin fallar.
"""

import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Crea un superusuario a partir de DJANGO_SUPERUSER_USERNAME/EMAIL/PASSWORD si todavía no existe.'

    def handle(self, *args, **options):
        username = os.environ.get('DJANGO_SUPERUSER_USERNAME')
        email = os.environ.get('DJANGO_SUPERUSER_EMAIL', '')
        password = os.environ.get('DJANGO_SUPERUSER_PASSWORD')

        if not username or not password:
            self.stdout.write('DJANGO_SUPERUSER_USERNAME/PASSWORD no definidos: no se crea ningún superusuario.')
            return

        User = get_user_model()
        if User.objects.filter(username=username).exists():
            self.stdout.write(f'El superusuario "{username}" ya existe, no se hace nada.')
            return

        User.objects.create_superuser(username=username, email=email, password=password)
        self.stdout.write(self.style.SUCCESS(f'Superusuario "{username}" creado correctamente.'))
