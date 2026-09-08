"""
Configuración general del proyecto Django "Sistema de Inventario".

Generado inicialmente por 'django-admin startproject' y ajustado a mano
para las necesidades del proyecto. Documentación oficial de settings:
https://docs.djangoproject.com/en/6.1/ref/settings/
"""

import os
from pathlib import Path

import dj_database_url

# BASE_DIR es la carpeta raíz del proyecto (donde está manage.py).
BASE_DIR = Path(__file__).resolve().parent.parent

# ¿Estamos corriendo en Render? Render inyecta esta variable de entorno
# automáticamente en todos sus servicios, así que nos sirve para saber si
# estamos "en producción" sin tener que configurar nada a mano. En local
# no existe, así que RENDER_EXTERNAL_HOSTNAME queda en None y el proyecto
# se comporta igual que siempre (SQLite, DEBUG=True...).
RENDER_EXTERNAL_HOSTNAME = os.environ.get('RENDER_EXTERNAL_HOSTNAME')


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
# configuración extra. Cómodo para desarrollar. En Render forzamos
# DEBUG=False automáticamente (nunca queremos páginas de error detalladas
# de cara al público). En local, si no defines la variable DEBUG, sigue
# en True.
DEBUG = os.environ.get('DEBUG', 'True' if not RENDER_EXTERNAL_HOSTNAME else 'False') == 'True'

# Con DEBUG=True, Django permite automáticamente localhost/127.0.0.1
# aunque ALLOWED_HOSTS esté vacío. En Render añadimos el dominio público
# que nos ha asignado (algo como "mi-app.onrender.com").
ALLOWED_HOSTS = []
if RENDER_EXTERNAL_HOSTNAME:
    ALLOWED_HOSTS.append(RENDER_EXTERNAL_HOSTNAME)


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

# WhiteNoise sirve los archivos estáticos (CSS, JS) directamente desde el
# propio proceso de Django, sin necesitar un servidor aparte (nginx, un
# CDN...) delante. Solo lo activamos en Render: en local, con DEBUG=True,
# Django ya sirve los estáticos por su cuenta. Se inserta justo después
# de SecurityMiddleware, la posición que recomienda la propia
# documentación de WhiteNoise.
if RENDER_EXTERNAL_HOSTNAME:
    MIDDLEWARE.insert(1, 'whitenoise.middleware.WhiteNoiseMiddleware')

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


# --- Base de datos ---
# https://docs.djangoproject.com/en/6.1/ref/settings/#databases
#
# En local seguimos usando SQLite. En Render, el servicio web no tiene
# disco persistente en el plan gratuito, así que si existe la variable
# de entorno DATABASE_URL (Render la inyecta sola al conectar una base
# de datos PostgreSQL al servicio) la usamos en su lugar. dj_database_url
# traduce esa URL a la sintaxis que espera Django.
DATABASES = {
    'default': dj_database_url.config(
        default=f'sqlite:///{BASE_DIR / "db.sqlite3"}',
        conn_max_age=600,
    )
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
# Carpeta donde `collectstatic` reúne todos los estáticos para poder
# servirlos en producción. En local no hace falta tocarla.
STATIC_ROOT = BASE_DIR / 'staticfiles'

STORAGES = {
    'default': {
        'BACKEND': 'django.core.files.storage.FileSystemStorage',
    },
    'staticfiles': {
        # El almacenamiento "manifest" de WhiteNoise añade un hash al
        # nombre de cada archivo y los comprime, para que el navegador
        # pueda cachearlos "para siempre" sin servir una versión vieja
        # tras un despliegue nuevo. Necesita el manifiesto que genera
        # `collectstatic`, así que solo se activa en Render (donde el
        # build siempre lo ejecuta antes de arrancar); en local se usa
        # el almacenamiento normal de Django.
        'BACKEND': (
            'whitenoise.storage.CompressedManifestStaticFilesStorage'
            if RENDER_EXTERNAL_HOSTNAME
            else 'django.contrib.staticfiles.storage.StaticFilesStorage'
        ),
    },
}

# --- Seguridad HTTPS (solo aplica cuando Render sirve el sitio) ---
if RENDER_EXTERNAL_HOSTNAME:
    # El navegador debe enviar el formulario de login/registro a la misma
    # URL https://... por la que llegó; si no se declara aquí, Django
    # rechaza el POST con un error de CSRF al estar detrás de un proxy.
    CSRF_TRUSTED_ORIGINS = [f'https://{RENDER_EXTERNAL_HOSTNAME}']
    # Render termina el HTTPS en su proxy y nos reenvía la petición por
    # HTTP puro con esta cabecera indicando el protocolo original.
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

    # Ajustes que recomienda `manage.py check --deploy`: fuerzan HTTPS y
    # marcan las cookies como "solo por conexión segura". Dentro de este
    # `if` porque en local (sin HTTPS) romperían el login.
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    # No activamos SECURE_HSTS_INCLUDE_SUBDOMAINS ni _PRELOAD porque el
    # dominio es un subdominio compartido de onrender.com, no uno propio.
    SECURE_HSTS_SECONDS = 3600

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
