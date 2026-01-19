from schedule.models import Lesson, Group

print("=== QUICK LESSONS WITH ZOOM ===")
quick = Lesson.objects.filter(is_quick_lesson=True, zoom_join_url__isnull=False)
print("Count:", quick.count())
for l in quick:
    gname = l.group.name if l.group else "NO_GROUP"
    print("  ID=%s group='%s' zoom=%s" % (l.id, gname, l.zoom_join_url[:50] if l.zoom_join_url else None))
    if l.group:
        students = l.group.students.all()
        print("    Students in this group:", [s.email for s in students[:5]])

print("")
print("=== GROUP 1.1 INFO ===")
g = Group.objects.filter(name__icontains="1.1").first()
if g:
    print("Group ID=%s, name=%s" % (g.id, g.name))
    print("Students:", [s.email for s in g.students.all()])
