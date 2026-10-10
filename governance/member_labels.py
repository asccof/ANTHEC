"""Explicit Phase 2 interface vocabulary; machine states remain stable."""

from .institutional_labels import LABELS as INSTITUTIONAL

ROWS = {
    "administration": (
        "إدارة العضوية",
        "Administration des adhésions",
        "Membership administration",
    ),
    "approve": ("الموافقة", "Approuver", "Approve"),
    "reject": ("الرفض", "Refuser", "Reject"),
    "payment": ("التحقق المالي", "Vérification financière", "Financial verification"),
    "amount": ("المبلغ بالدرهم", "Montant en MAD", "Amount in MAD"),
    "method": ("طريقة الأداء", "Mode de paiement", "Payment method"),
    "cash": ("نقدًا", "Espèces", "Cash"),
    "transfer": ("تحويل بنكي", "Virement", "Bank transfer"),
    "proof_reference": (
        "مرجع الإثبات الداخلي",
        "Référence justificative privée",
        "Private proof reference",
    ),
    "exempt": ("إعفاء استثنائي موثق", "Exonération documentée", "Documented exemption"),
    "refund": ("قرار الاسترجاع", "Décision de remboursement", "Refund decision"),
    "payment_id": ("الأداء الأصلي", "Paiement initial", "Original payment"),
    "approved": ("موافق عليه", "Approuvée", "Approved"),
    "person_id": ("سجل الشخص", "Dossier personne", "Person record"),
    "user_id": ("الحساب المستهدف", "Compte cible", "Target account"),
    "identities": (
        "ربط سجل سابق بحساب",
        "Rattacher un dossier existant",
        "Link existing person to account",
    ),
    "link_notice": (
        "سجّل إثبات التحقق من الهوية في سبب القرار. الربط لا ينقل السجلات المرتبطة ولا يدمجها ولا يمنح صلاحيات.",
        "Consignez la vérification d’identité dans le motif. Aucun transfert, fusion ou privilège implicite.",
        "Record identity verification evidence in the reason. Linking does not transfer/merge linked records or grant privileges.",
    ),
    "document_id": ("الوثيقة", "Document", "Document"),
    "membership_card": ("بطاقة العضوية", "Carte de membre", "Membership card"),
    "gold_card": (
        "بطاقة العضوية الذهبية",
        "Carte de membre dorée",
        "Gold membership card",
    ),
    "professional_certificate": (
        "شهادة الاعتماد المهني الجمعوي",
        "Certificat d’accréditation professionnelle associative",
        "Association professional accreditation certificate",
    ),
    "paid": ("مجموع الأداء المتحقق", "Paiements vérifiés", "Verified payments"),
    "refunded": (
        "مجموع الاسترجاع الموافق عليه",
        "Remboursements approuvés",
        "Approved refunds",
    ),
    "receipt": ("مرجع الوصل", "Référence du reçu", "Receipt reference"),
    "membership_start": ("بداية العضوية", "Début d’adhésion", "Membership start"),
    "membership_end": (
        "نهاية العضوية (غير مشمولة)",
        "Fin d’adhésion (exclusive)",
        "Membership end (exclusive)",
    ),
    "members": ("فضاء العضو", "Espace membre", "Member area"),
    "signup": ("إنشاء حساب", "Créer un compte", "Create account"),
    "login": ("تسجيل الدخول", "Connexion", "Sign in"),
    "logout": ("تسجيل الخروج", "Déconnexion", "Sign out"),
    "username": ("اسم المستخدم", "Nom d’utilisateur", "Username"),
    "password": ("كلمة المرور", "Mot de passe", "Password"),
    "password1": ("كلمة المرور", "Mot de passe", "Password"),
    "password2": ("تأكيد كلمة المرور", "Confirmer le mot de passe", "Confirm password"),
    "old_password": ("كلمة المرور الحالية", "Mot de passe actuel", "Current password"),
    "new_password1": ("كلمة المرور الجديدة", "Nouveau mot de passe", "New password"),
    "new_password2": (
        "تأكيد كلمة المرور الجديدة",
        "Confirmer le nouveau mot de passe",
        "Confirm new password",
    ),
    "change_password": (
        "تغيير كلمة المرور",
        "Changer le mot de passe",
        "Change password",
    ),
    "profile": ("الملف الشخصي", "Profil", "Profile"),
    "full_name": ("الاسم الكامل", "Nom complet", "Full name"),
    "contact": ("بريد التواصل الخاص", "Courriel privé", "Private contact email"),
    "directory_consent": (
        "أوافق اختياريًا على إدراج اسمي في دليل منفصل؛ لم يُفعّل النشر بعد",
        "Consentement facultatif à un annuaire distinct ; publication non activée",
        "Optional consent to a separate directory; publication not activated",
    ),
    "notice": (
        "اطلعت على إشعار التحقق: بعد الموافقة يظهر الاسم ونوع الوثيقة ومرجعها وتواريخها وحالتها لمن يحمل QR أو المرجع ورمز التحقق؛ لا تظهر بيانات الاتصال أو الأسباب الداخلية.",
        "Avis de vérification lu : après approbation, nom, type, référence, dates et statut sont accessibles avec QR ou référence et code ; contacts et motifs internes restent privés.",
        "Verification notice read: after approval, name, document type, reference, dates and status are available with QR or reference plus code; contacts and internal reasons remain private.",
    ),
    "apply": ("طلب الانخراط", "Demande d’adhésion", "Membership application"),
    "tier": ("نوع العضوية", "Catégorie", "Membership tier"),
    "general": ("عضو عام", "Membre général", "General member"),
    "affiliate": ("عضو منتسب", "Membre affilié", "Affiliated member"),
    "advanced": ("عضو متقدم", "Membre avancé", "Advanced member"),
    "accredited": ("عضو معتمد", "Membre accrédité", "Accredited member"),
    "honorary": ("عضو شرفي", "Membre honoraire", "Honorary member"),
    "submitted": ("قيد المراجعة", "En cours d’examen", "Under review"),
    "approved": ("موافق عليه", "Approuvée", "Approved"),
    "rejected": ("مرفوض", "Refusée", "Rejected"),
    "applications": ("طلباتي", "Mes demandes", "My applications"),
    "quote": ("المبلغ المثبت بالدرهم", "Montant fixé en MAD", "Fixed amount in MAD"),
    "quoted_on": ("تاريخ تثبيت السعر", "Date du tarif fixé", "Quote date"),
    "error": (
        "تعذر تنفيذ الطلب؛ تحقق من البيانات والحالة الحالية.",
        "Impossible de traiter la demande ; vérifiez les données et le statut.",
        "Unable to process; check the data and current status.",
    ),
    "limited": (
        "محاولات كثيرة؛ حاول لاحقًا.",
        "Trop de tentatives ; réessayez plus tard.",
        "Too many attempts; try later.",
    ),
    "demo": (
        "بيئة تطوير ببيانات اصطناعية فقط. لا ترسل بيانات أشخاص حقيقيين.",
        "Développement avec données fictives uniquement. Aucune donnée réelle.",
        "Development with synthetic data only. Do not submit real-person data.",
    ),
    "terms": (
        "الطلب والأداء لا يمنحان العضوية؛ القرار للإدارة. الاعتماد جمعوي وليس ترخيصًا حكوميًا.",
        "Demande et paiement ne confèrent pas l’adhésion ; décision administrative. Accréditation associative, pas une licence officielle.",
        "Application and payment do not grant membership; administration decides. Association accreditation is not a government licence.",
    ),
    "existing_record": (
        "إذا سبق أن سجلتك الإدارة، اطلب ربط حسابك بالسجل قبل إنشاء ملف جديد؛ لا تتم المطابقة بالاسم أو البريد تلقائيًا.",
        "Si un dossier existe déjà, demandez son rattachement avant de créer un profil ; aucune correspondance automatique par nom ou courriel.",
        "If administration already recorded you, request account linking before creating a profile; no automatic name/email matching.",
    ),
}


def vocabulary(language="ar"):
    language = language if language in ("ar", "fr", "en") else "ar"
    index = ("ar", "fr", "en").index(language)
    return language, {
        **INSTITUTIONAL[language],
        **{k: v[index] for k, v in ROWS.items()},
    }
