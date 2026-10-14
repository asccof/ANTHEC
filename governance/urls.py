from django.urls import path
from . import (
    certificate_asset_views,
    pdf_views,
    portrait_views,
    security,
    views,
    institutional_views,
    member_views,
    membership_admin_views,
    partner_views,
    accreditation_views,
    activity_views,
)

urlpatterns = [
    path("activities/", activity_views.listing, name="activity_list"),
    path("activities/<int:activity_id>/", activity_views.participate, name="activity_participate"),
    path("operations/activities/", activity_views.register, name="activity_admin_register"),
    path("operations/activities/<int:activity_id>/", activity_views.detail, name="activity_admin_detail"),
    path("operations/activities/registrations/<int:registration_id>/", activity_views.admission, name="activity_admission"),
    path("operations/accreditation/", accreditation_views.register, name="accreditation_register"),
    path("operations/accreditation/<int:case_id>/", accreditation_views.detail, name="accreditation_case"),
    path("partners/", partner_views.listing, name="partners"),
    path("partners/request/", partner_views.request_partnership, name="partnership_request"),
    path("operations/partners/", partner_views.register, name="partnership_register"),
    path("operations/partners/requests/<int:request_id>/", partner_views.review, name="partnership_review"),
    path("operations/partners/<int:partner_id>/", partner_views.detail, name="partner_detail"),
    path("operations/certificate-assets/", certificate_asset_views.manage, name="certificate_assets"),
    path("private-certificate-assets/<uuid:serial>/", certificate_asset_views.image, name="certificate_asset_image"),
    path(
        "my-documents/<int:document_id>/prepare/",
        pdf_views.prepare,
        name="document_pdf_prepare",
    ),
    path(
        "my-documents/<int:document_id>/pdf/", pdf_views.download, name="document_pdf"
    ),
    path(
        "my-documents/<int:document_id>/preview/",
        pdf_views.download,
        {"preview": True},
        name="document_pdf_preview",
    ),
    path("members/portrait/", portrait_views.upload, name="portrait_upload"),
    path("operations/portraits/", portrait_views.review, name="portrait_review"),
    path(
        "private-portraits/<uuid:serial>/", portrait_views.image, name="portrait_image"
    ),
    path("members/renew/", member_views.renew, name="member_renew"),
    path("members/documents/", member_views.documents, name="member_documents"),
    path(
        "members/applications/<int:application_id>/",
        member_views.application_detail,
        name="member_application",
    ),
    path(
        "operations/membership/",
        membership_admin_views.register,
        name="membership_admin_register",
    ),
    path(
        "operations/membership/identities/",
        membership_admin_views.identities,
        name="membership_identities",
    ),
    path(
        "operations/membership/<int:application_id>/",
        membership_admin_views.detail,
        name="membership_admin_detail",
    ),
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
