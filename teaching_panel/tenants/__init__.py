"""
Tenants app — мультитенантная архитектура для платформы LectioSpace.

Каждая организация (Tenant) = отдельный tenant на одном движке.
Разделение через subdomain: anna.lectiospace.ru → Tenant(slug='anna')
"""
