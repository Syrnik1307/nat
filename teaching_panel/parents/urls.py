from django.urls import path
from . import views

urlpatterns = [
    # Teacher-facing (auth required)
    path('access/', views.TeacherCreateAccessView.as_view(), name='parent-access-create'),
    path('grants/', views.TeacherGrantListView.as_view(), name='parent-grants-list'),
    path('grants/<int:grant_id>/', views.TeacherGrantDetailView.as_view(), name='parent-grant-detail'),
    path('grants/<int:grant_id>/comments/', views.TeacherCommentView.as_view(), name='parent-grant-comments'),
    path('grants/<int:grant_id>/comments/<int:comment_id>/', views.TeacherCommentDeleteView.as_view(), name='parent-comment-delete'),
    path('access/student/<int:student_id>/group/<int:group_id>/', views.TeacherGetStudentAccessView.as_view(), name='parent-access-student'),

    # Parent-facing (no auth, token-based)
    path('dashboard/<uuid:token>/', views.ParentDashboardView.as_view(), name='parent-dashboard'),
]
