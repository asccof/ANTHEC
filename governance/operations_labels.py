"""Explicit private operational vocabulary; no policy or permission changes."""
ROWS = {
    "directors": ("إدارة المديرين", "Gestion des directeurs", "Director management"),
    "pricing": ("إدارة أسعار العضوية", "Tarifs des adhésions", "Membership pricing"),
    "primary": ("المدير الرئيسي", "Directeur principal", "Primary director"),
    "primary_notice": ("المدير الرئيسي ثابت ولا يمكن تغييره من هذه الواجهة. إدارة التفويضات من اختصاصه وحده.", "Le directeur principal ne peut pas être modifié ici. Lui seul gère les délégations.", "The primary director cannot be changed here. Only the primary manages delegations."),
    "user": ("الحساب المستهدف", "Compte cible", "Target account"),
    "decision": ("القرار", "Décision", "Decision"),
    "grant": ("منح أو تجديد التفويض", "Accorder ou renouveler", "Grant or renew delegation"),
    "revoke": ("إلغاء التفويض", "Révoquer", "Revoke delegation"),
    "active": ("نشط", "Actif", "Active"),
    "inactive": ("ملغى", "Révoqué", "Revoked"),
    "reason": ("سبب القرار", "Motif", "Decision reason"),
    "confirm": ("أؤكد القرار المحدد أعلاه", "Je confirme la décision ci-dessus", "I confirm the decision above"),
    "save": ("تنفيذ القرار", "Appliquer la décision", "Apply decision"),
    "history": ("سجل القرارات", "Historique", "Decision history"),
    "empty": ("لا توجد سجلات", "Aucun dossier", "No records"),
    "epoch": ("إصدار التفويض", "Version du mandat", "Delegation version"),
    "price_notice": ("الأسعار السابقة محفوظة. التعديل مستقبلي فقط ولا يغيّر المبالغ المثبتة في الطلبات السابقة. المؤسس والشرفي مجانيان.", "Historique conservé. Modification future uniquement, sans changer les devis existants. Fondateurs et honoraires gratuits.", "History is preserved. Future changes only; existing application quotes are unchanged. Founder and honorary remain free."),
    "tier": ("مستوى العضوية", "Niveau", "Membership tier"),
    "amount": ("المبلغ بالدرهم", "Montant en MAD", "Amount in MAD"),
    "starts_at": ("بداية السريان — التوقيت العالمي UTC", "Prise d'effet — heure UTC", "Effective from — UTC"),
    "schedule": ("برمجة سعر مستقبلي", "Programmer un tarif", "Schedule future price"),
    "current": ("الأسعار الحالية", "Tarifs actuels", "Current prices"),
    "versions": ("الإصدارات السابقة والمبرمجة", "Historique et tarifs programmés", "Historical and scheduled versions"),
    "testing": ("تجربة خاصة ببيانات اصطناعية؛ تغيير التفويض لا يفتح الموقع لغير المالك. التسجيلات والمدفوعات والإصدار الرسمي معطلة.", "Test privé fictif ; déléguer ne donne pas accès au site privé. Inscriptions, paiements et émission désactivés.", "Private synthetic testing; delegation does not admit anyone else to the private site. Registration, payments and issuance remain disabled."),
    "error": ("تعذر التنفيذ. تحقق من القرار والبيانات وأعد التحقق الأمني عند الحاجة.", "Opération impossible. Vérifiez les données et la réauthentification récente.", "Unable to apply. Check the decision, data and recent reauthentication."),
    "reauth": ("إعادة التحقق الأمني", "Se réauthentifier", "Reauthenticate"),
}
def vocabulary(language="ar"):
    language = language if language in ("ar", "fr", "en") else "ar"
    index = ("ar", "fr", "en").index(language)
    return language, {key: values[index] for key, values in ROWS.items()}
