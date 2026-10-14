"""
WSGI config for Deduplicate project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/2.1/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Deduplicate.settings')

application = get_wsgi_application()

# Expose app for Vercel serverless deployment
app = application
