#!/bin/bash
# Генерирует новый SECRET_KEY для продакшена

from django.core.management.utils import get_random_secret_key

secret = get_random_secret_key()
print(f"SECRET_KEY={secret}")
