"""Shared public navigation/copy; never query member or request data."""
from content.presentation import vocabulary

WORDS = {
    'return_home': ('الرئيسية', 'Accueil', 'Home'),
    'partners_intro': ('التعاون لخدمة المعرفة وجودة الممارسة', 'Coopérer au service du savoir et des pratiques', 'Working together for knowledge and quality practice'),
    'partners_detail': ('نعرض هنا الشراكات التي اعتمدتها الإدارة وأذنت بإظهارها. يمكن للمؤسسات اقتراح تعاون في التوعية والتكوين وتبادل الخبرات.', 'Cette page présente les partenariats approuvés et publiés par l’administration. Les organisations peuvent proposer des actions de sensibilisation, de formation ou de partage d’expérience.', 'This page presents partnerships approved and published by the administration. Organizations can propose awareness, training or knowledge-sharing initiatives.'),
    'proposal_intro': ('عرّف بمؤسستك وبالتعاون الذي تقترحه. يراجع الفريق الطلب قبل أي قرار؛ إرسال الطلب لا ينشئ شراكة أو اعتمادًا.', 'Présentez votre organisation et votre proposition. L’équipe examine la demande avant toute décision ; son envoi ne crée ni partenariat ni accréditation.', 'Introduce your organization and proposed collaboration. The team reviews requests before deciding; submission does not grant partnership or accreditation.'),
    'proposal_private': ('بريد التواصل ورسالة الطلب مخصصان للمراجعة الإدارية ولا يظهران في صفحة الشركاء. لا ترسل بيانات صحية أو ملفات أشخاص.', 'Le courriel et le message sont réservés à l’examen administratif et ne figurent pas dans l’annuaire public. Ne transmettez pas de données de santé ou de dossiers personnels.', 'Contact email and proposal are for administrative review and are not shown in the public listing. Do not submit health information or personal case files.'),
    'send_proposal': ('إرسال طلب الشراكة', 'Envoyer la demande', 'Submit partnership request'),
    'return_partners': ('العودة إلى الشركاء', 'Retour aux partenaires', 'Back to partners'),
    'verify_intro': ('أدخل مرجع الوثيقة ورمز التحقق المطبوع عليها، أو افتح الرابط الموجود في رمز QR.', 'Saisissez la référence et le code imprimés sur le document, ou ouvrez le lien de son QR code.', 'Enter the reference and verification code printed on the document, or open its QR link.'),
    'verify_privacy': ('التحقق يخص وثيقة محددة؛ لا يوجد بحث عام بالاسم، ولا تُعرض معلومات التواصل أو ملفات العضو الخاصة.', 'La vérification concerne un document précis : aucune recherche par nom ni accès aux coordonnées ou dossiers privés.', 'Verification concerns one specific document: there is no name search or access to private contacts or member files.'),
    'verify_error': ('لم يُعثر على وثيقة بهذه البيانات. تحقق من المرجع والرمز وحاول مجددًا.', 'Aucun document ne correspond. Vérifiez la référence et le code puis réessayez.', 'No document matches these details. Check the reference and code and try again.'),
    'verify_limit': ('طلبات كثيرة. انتظر قليلًا قبل إعادة المحاولة.', 'Trop de tentatives. Patientez avant de réessayer.', 'Too many attempts. Please wait before trying again.'),
    'verify_result': ('نتيجة التحقق', 'Résultat de vérification', 'Verification result'),
    'verify_again': ('التحقق من وثيقة أخرى', 'Vérifier un autre document', 'Verify another document'),
    'published': ('ظاهر للعموم', 'Visible au public', 'Publicly visible'),
    'hidden': ('غير ظاهر للعموم', 'Masqué au public', 'Hidden from public'),
    'open_record': ('فتح الملف', 'Ouvrir le dossier', 'Open record'),
    'review_decision': ('حفظ قرار مراجعة الشراكة', 'Enregistrer la décision', 'Save review decision'),
    'save_partner': ('حفظ بيانات الشريك وحالته', 'Enregistrer le partenaire et son statut', 'Save partner details and state'),
    'review_note': ('القبول ينشئ سجل شريك غير ظاهر؛ الإظهار للعموم قرار مستقل يتطلب الصلاحية المناسبة.', 'L’approbation crée un partenaire masqué ; sa publication est une décision distincte soumise à autorisation.', 'Approval creates a hidden partner record; publication is a separate authorized decision.'),
    'register_window': ('آخر 100 طلب وآخر 100 شريك، من الأحدث إلى الأقدم.', 'Les 100 dernières demandes et les 100 derniers partenaires.', 'The latest 100 requests and 100 partner records.'),
}


def labels(language):
    language = language if language in ('ar', 'fr', 'en') else 'ar'
    result = vocabulary(language)
    result.update({key: values[('ar','fr','en').index(language)] for key,values in WORDS.items()})
    return result
