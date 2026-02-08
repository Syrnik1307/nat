"""
Tenants app — multi-tenant архитектура для штамповки онлайн-школ.

Каждая школа (School) = отдельный tenant на одном движке.
Разделение через subdomain: anna.lectiospace.ru → School(slug='anna')

Модель данных:
    School ← 1 owner (учитель-владелец)
    School ← N SchoolMembership (кто в этой школе)
    School ← FK из Group, Lesson, Homework и т.д. (добавляется позже)
"""
