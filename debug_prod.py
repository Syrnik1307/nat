from schedule.models import Lesson, Group

print("=== ACTIVE LESSONS ===")
active = Lesson.objects.filter(is_active=True)
print("Count:", active.count())
for l in active:
    gname = l.group.name if l.group else "NO_GROUP"
    print("  ID=%s group='%s' is_quick=%s zoom=%s" % (l.id, gname, l.is_quick_lesson, bool(l.zoom_join_url)))
    if l.group:
        students = l.group.students.all()
        print("    Students:", [s.email for s in students])

print("")
print("=== GROUP 1.1 ===")
g = Group.objects.filter(name__icontains="1.1").first()
if g:
    print("Group ID=%s, name=%s" % (g.id, g.name))
    print("Students:", [s.email for s in g.students.all()])
