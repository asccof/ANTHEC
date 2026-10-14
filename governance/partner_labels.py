"""Manual AR/FR/EN labels; no external provider."""
WORDS = {
 'title': ('الشركاء','Partenaires','Partners'),
 'request_title': ('طلب شراكة','Demande de partenariat','Partnership request'),
 'administration': ('إدارة الشراكات','Administration des partenariats','Partnership administration'),
 'organization': ('المؤسسة','Organisation','Organization'),
 'contact_email': ('بريد التواصل الخاص','Courriel privé','Private contact email'),
 'message': ('وصف الشراكة المقترحة','Proposition de partenariat','Partnership proposal'),
 'notice_acknowledged': ('أوافق على حفظ هذه المعطيات لمراجعة الطلب. لا أرسل بيانات حساسة.','Je consens à la conservation pour examiner la demande. Aucune donnée sensible.','I consent to storage for request review. No sensitive data.'),
 'reason': ('سبب القرار','Motif de décision','Decision reason'),
 'decision': ('القرار','Décision','Decision'),
 'approved': ('مقبول','Acceptée','Approved'), 'rejected': ('مرفوض','Refusée','Rejected'),
 'submitted': ('قيد المراجعة','À examiner','Submitted'),
 'active': ('نشط','Actif','Active'), 'suspended': ('معلق','Suspendu','Suspended'), 'cancelled': ('ملغى','Annulé','Cancelled'),
 'state': ('الحالة','Statut','Status'), 'save': ('حفظ','Enregistrer','Save'),
 'empty': ('لا توجد سجلات','Aucun enregistrement','No records'),
 'name_ar': ('الاسم بالعربية','Nom en arabe','Arabic name'),
 'name_fr': ('الاسم بالفرنسية','Nom en français','French name'),
 'name_en': ('الاسم بالإنجليزية','Nom en anglais','English name'),
 'summary_ar': ('الوصف بالعربية','Description en arabe','Arabic summary'),
 'summary_fr': ('الوصف بالفرنسية','Description en français','French summary'),
 'summary_en': ('الوصف بالإنجليزية','Description en anglais','English summary'),
 'website': ('الموقع الرسمي','Site officiel','Official website'),
 'public_visible': ('إظهار للعموم بعد القرار الإداري','Visibilité publique après décision','Public visibility after administrative decision'),
 'received': ('تم تسجيل الطلب للمراجعة، وهذا ليس قبولًا للشراكة.','Demande enregistrée pour examen ; aucun partenariat accordé.','Request received for review; no partnership granted.'),
 'error': ('تعذر الحفظ؛ تحقق من المعطيات والمصادقة الحديثة.','Enregistrement impossible ; vérifiez les données et réauthentifiez-vous.','Unable to save; check data and recent reauthentication.'),
 'testing': ('تجربة خاصة ببيانات اصطناعية فقط. الطلبات والنشر العام معطلان.','Essai privé fictif. Demandes et publication publiques désactivées.','Private synthetic testing. Public submissions and publication disabled.'),
 'history': ('سجل القرارات','Historique des décisions','Decision history'),
}
def vocabulary(language):
    language = language if language in {'ar','fr','en'} else 'ar'
    index = ('ar','fr','en').index(language)
    return language, {key: value[index] for key,value in WORDS.items()}
