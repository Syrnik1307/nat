from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from .models import StudentSubmission

@shared_task(name='homework.tasks.notify_student_graded')
def notify_student_graded(submission_id: int):
    try:
        submission = StudentSubmission.objects.select_related('student', 'homework').get(id=submission_id)
    except StudentSubmission.DoesNotExist:
        return
    
    student = submission.student
    subject = f"Проверено: {submission.homework.title}"
    total = submission.total_score or 0
    message = (
        f"Здравствуйте, {student.first_name or student.email}!\n\n"
        f"Ваша работа по заданию '{submission.homework.title}' была проверена.\n"
        f"Итоговый балл: {total}.\n\n"
        f"Зайдите в систему, чтобы увидеть подробности и комментарии."
    )
    send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [student.email],
        fail_silently=True,
    )
