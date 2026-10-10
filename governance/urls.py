from django.urls import path
from . import security, views, institutional_views, member_views

urlpatterns = [
    path("members/", member_views.home, name="member_home"),
    path(
        "members/signup/",
        member_views.account,
        {"mode": "signup"},
        name="member_signup",
    ),
    path(
        "members/login/", member_views.account, {"mode": "login"}, name="member_login"
    ),
    path("members/logout/", member_views.signout, name="member_logout"),
    path("members/password/", member_views.password, name="member_password"),
    path("members/profile/", member_views.profile, name="member_profile"),
    path("members/apply/", member_views.apply, name="member_apply"),
    path(
        "operations/institutional/",
        institutional_views.register,
        name="institutional_register",
    ),
    path(
        "operations/institutional/<int:role_id>/",
        institutional_views.detail,
        name="institutional_detail",
    ),
    path("security/challenge/", security.challenge, name="security_challenge"),
    path("security/enroll/", security.enroll, name="security_enroll"),
    path("operations/<str:action>/", views.operation),
    path("verify/", views.verify, name="document_verify"),
    path("my-documents/<int:document_id>/", views.download),
    path("registrations/request/", views.registration_request),
]
