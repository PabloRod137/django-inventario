"""
Configuración general del proyecto Django "Sistema de Inventario".

Generado inicialmente por 'django-admin startproject' y ajustado a mano
para las necesidades del proyecto. Documentación oficial de settings:
https://docs.djangoproject.com/en/6.1/ref/settings/
"""

import os
from pathlib import Path

# BASE_DIR es la carpeta raíz del proyecto (donde está manage.py).
BASE_DIR = Path(__file__).resolve().parent.parent


# --- Seguridad básica ---
#
# SECRET_KEY firma internamente cookies de sesión, tokens CSRF, etc. En
# producción NUNCA debería ir escrita en el código ni subida a un repo
# público. Aquí se lee de la variable de entorno DJANGO_SECRET_KEY y, si
# no existe (como al clonar este repo para probarlo en local), se usa una
# clave de repuesto marcada como 'django-insecure-' (la misma convención
# que usa Django para avisar de que no es apta para producción).
SECRET_KEY = os.environ.get(
    'DJANGO_SECRET_KEY',
    'django-insecure-**$(8d^h#gwflm@cc#9a!z+c9!_4w&$o_asqwlgsep60-vv836',
)

# DEBUG=True: páginas de error detalladas y estáticos servidos sin
# configuración extra. Cómodo para desarrollar. En producción, False.
DEBUG = True

# Con DEBUG=True, Django permite automáticamente localhost/127.0.0.1
# aunque ALLOWED_HOSTS esté vacío.
ALLOWED_HOSTS = []


# --- Aplicaciones instaladas ---
# Las seis primeras vienen con Django (admin, autenticación, tipos de
# contenido, sesiones, mensajes flash, estáticos). 'inventory' es nuestra app.
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'inventory',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        # Plantillas "compartidas" del proyecto (base.html, registro/login).
        # Las de cada app (templates/inventory/...) las encuentra Django
        # solo, gracias a APP_DIRS=True.
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'


# Database
# https://docs.djangoproject.com/en/6.1/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}


# Password validation
# https://docs.djangoproject.com/en/6.1/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# --- Internacionalización ---
# https://docs.djangoproject.com/en/6.1/topics/i18n/

LANGUAGE_CODE = 'es-es'

# Con USE_TZ=True, Django guarda TODAS las fechas en UTC en la base de
# datos y usa TIME_ZONE solo para convertir de/hacia UTC al mostrar o
# introducir una fecha. Ver los comentarios en inventory/views.py
# (movements_chart) sobre por qué esto importa incluso para agrupar
# movimientos "por día".
TIME_ZONE = 'Europe/Madrid'

USE_I18N = True
USE_TZ = True


# --- Archivos estáticos (CSS, JS, imágenes) ---
# https://docs.djangoproject.com/en/6.1/howto/static-files/

STATIC_URL = 'static/'
STATICFILES_DIRS = [BASE_DIR / 'static']

# --- Autenticación ---
LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'product_list'
LOGOUT_REDIRECT_URL = 'login'


# --- Correo ---
# https://docs.djangoproject.com/en/6.1/topics/email/
#
# Este proyecto no envía emails, pero se deja la configuración lista con
# el backend de "consola" por coherencia con los otros proyectos del
# máster y por si en el futuro se quisiera avisar por email de alertas
# de stock mínimo, por ejemplo.
MAILERS = {
    'default': {
        'BACKEND': 'django.core.mail.backends.console.EmailBackend',
    },
}
