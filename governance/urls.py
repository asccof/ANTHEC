from django.urls import path
from . import security, views

urlpatterns = [
    path("security/challenge/", security.challenge, name="security_challenge"),
    path("security/enroll/", security.enroll, name="security_enroll"),
    path("operations/<str:action>/", views.operation),
    path("verify/", views.verify, name="document_verify"),
    path("my-documents/<int:document_id>/", views.download),
    path("registrations/request/", views.registration_request),
]
