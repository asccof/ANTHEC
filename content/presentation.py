"""Public presentation copy only; no personal or private assessment data."""
from django.utils import timezone
from governance.models import Price
from governance.member_labels import vocabulary as member_vocabulary

ROWS = {
 "name": ("الجمعية الوطنية للعلاج النفسي والأسري والكوتشينغ", "Association nationale de psychothérapie, thérapie familiale et coaching", "National association for psychotherapy, family therapy and coaching"),
 "nav": ("التنقل الرئيسي", "Navigation principale", "Main navigation"),
 "languages": ("اللغات", "Langues", "Languages"),
 "skip": ("انتقل إلى المحتوى", "Aller au contenu", "Skip to content"),
 "home": ("الرئيسية", "Accueil", "Home"),
 "about": ("عن الجمعية", "L’association", "About"),
 "memberships": ("العضوية", "Adhésion", "Membership"),
 "accreditation": ("الاعتماد الجمعوي", "Accréditation associative", "Association accreditation"),
 "activities": ("الأنشطة والمشاركة", "Activités et participation", "Activities and participation"),
 "partners": ("الشركاء", "Partenaires", "Partners"),
 "member_area": ("فضاء العضو", "Espace membre", "Member area"),
 "admin_area": ("لوحة الإدارة", "Administration", "Administration"),
 "apply": ("طلب الانخراط", "Demander l’adhésion", "Apply for membership"),
 "eyebrow": ("انتماء · تطوير · تعاون", "Appartenance · Développement · Coopération", "Belonging · Development · Cooperation"),
 "hero": ("فضاء للانتماء والتطوير المهني", "Un espace d’appartenance et de développement professionnel", "A space for belonging and professional development"),
 "intro": ("اكتشف مسارات العضوية والاعتماد الجمعوي والأنشطة والشراكات، ضمن إجراءات إدارية واضحة وموثقة.", "Découvrez les parcours d’adhésion, d’accréditation associative, d’activités et de partenariat, avec des décisions administratives documentées.", "Explore membership, association accreditation, activities and partnerships through documented administrative processes."),
 "explore": ("اكتشف مسارات العضوية", "Explorer les adhésions", "Explore membership"),
 "testing": ("نسخة خاصة للتجارب", "Version privée de test", "Private testing version"),
 "testing_detail": ("بيانات اصطناعية فقط. التسجيلات والمدفوعات وإصدار الوثائق والدعوات الرسمية معطلة. هذه معاينة وليست إطلاقًا رسميًا.", "Données fictives uniquement. Inscriptions, paiements, documents et invitations désactivés. Aperçu, sans lancement officiel.", "Synthetic data only. Registration, payments, official documents and invitations are disabled. This is a preview, not an official launch."),
 "closed": ("التسجيل معطل أثناء التجربة", "Inscriptions désactivées en test", "Registration disabled during testing"),
 "pathways": ("مسارات واضحة، وقرارات موثقة", "Des parcours clairs, des décisions documentées", "Clear pathways, documented decisions"),
 "membership_intro": ("الأسعار السنوية السارية حاليًا. تُثبت الرسوم في الطلب، وتبدأ الصلاحية عند الموافقة الإدارية النهائية.", "Tarifs annuels actuellement en vigueur. Le devis est fixé à la demande ; la validité commence à l’approbation administrative finale.", "Current annual prices. The application retains its quote; validity starts at final administrative approval."),
 "annual": ("درهم / سنة", "MAD / an", "MAD / year"),
 "unconfigured": ("تُحدد إداريًا", "À définir par l’administration", "Set by administration"),
 "level3": ("يشمل الاعتماد المهني الجمعوي وبطاقة ذهبية وشهادة منفصلة عند الموافقة أو التجديد.", "Inclut l’accréditation professionnelle associative, une carte dorée et un certificat distinct à l’approbation ou au renouvellement.", "Includes association professional accreditation, a gold card and a separate certificate upon approval or renewal."),
 "other_tiers": ("عضوية سنوية؛ لا تمنح اعتمادًا مهنيًا تلقائيًا.", "Adhésion annuelle, sans accréditation professionnelle automatique.", "Annual membership without automatic professional accreditation."),
 "permanent": ("العضو المؤسس والعضو الشرفي", "Membres fondateurs et honoraires", "Founder and honorary members"),
 "permanent_detail": ("صفتان مجانيتان ودائمتان بقرار إداري، دون تجديد سنوي أو صلاحيات إدارية تلقائية.", "Désignations gratuites et permanentes sur décision administrative, sans renouvellement annuel ni pouvoir administratif automatique.", "Free permanent designations by administrative decision, without annual renewal or automatic administrative powers."),
 "individual": ("اعتماد فردي", "Accréditation individuelle", "Individual accreditation"),
 "institution": ("اعتماد مؤسسة", "Accréditation d’institution", "Institution accreditation"),
 "course": ("اعتماد دورة", "Accréditation de formation", "Course accreditation"),
 "one_year": ("الصلاحية سنة واحدة وفق القرار الإداري.", "Validité d’un an selon la décision administrative.", "One-year validity under the administrative decision."),
 "course_term": ("الصلاحية مرتبطة بالمدة المعتمدة للدورة.", "Validité liée à la durée approuvée de la formation.", "Validity follows the approved course duration."),
 "private_terms": ("المعايير والتقييم والرسوم التفصيلية تُناقش مع الإدارة مباشرة ولا تُنشر هنا.", "Critères, évaluation et frais détaillés sont traités directement avec l’administration et ne sont pas publiés ici.", "Detailed criteria, assessment and fees are handled directly with administration and are not published here."),
 "not_licence": ("الاعتماد جمعوي وليس ترخيصًا حكوميًا لمزاولة مهنة.", "Accréditation associative, et non une autorisation publique d’exercer.", "Association accreditation is not a government professional licence."),
 "participate": ("المشاركة والتعاون", "Participation et coopération", "Participation and cooperation"),
 "activities_detail": ("طلبات المشاركة تخضع لموافقة الإدارة. مشاركة القاصر عبر وليه وموافقته الصريحة وفق شروط النشاط.", "Participation soumise à l’accord administratif. Les mineurs participent par leur représentant légal avec consentement explicite selon les conditions de l’activité.", "Participation requires administrative acceptance. Minors apply through a legal guardian with explicit consent under activity conditions."),
 "partners_detail": ("تُراجع طلبات الشراكة إداريًا قبل اعتمادها ونشرها. الشراكة لا تمنح عضوية أو اعتمادًا تلقائيًا.", "Les partenariats sont examinés avant approbation et publication, sans adhésion ni accréditation automatique.", "Partnerships are reviewed before approval and publication, without automatic membership or accreditation."),
 "partnership_request": ("اقتراح شراكة", "Proposer un partenariat", "Propose a partnership"),
 "privacy": ("الخصوصية والتحقق", "Confidentialité et vérification", "Privacy and verification"),
 "privacy_detail": ("بيانات الطلبات والتقييمات داخلية. التحقق من الوثائق يتم بمرجعها ورمزها أو رمز QR، وليس بالبحث عن الأسماء؛ والتحقق الرسمي معطل في نسخة التجربة.", "Demandes et évaluations restent privées. Les documents se vérifient par référence et code ou QR, sans recherche par nom ; vérification officielle désactivée en test.", "Applications and assessments remain private. Document checks use reference and code or QR, without name search; official verification is disabled during testing."),
 "editorial": ("المحتوى المؤسسي", "Contenu institutionnel", "Institutional content"),
 "footer": ("انتماء مسؤول، ومسارات موثقة.", "Une appartenance responsable, des parcours documentés.", "Responsible belonging, documented pathways."),
}
def vocabulary(language):
    language = language if language in ("ar", "fr", "en") else "ar"
    index = ("ar", "fr", "en").index(language)
    return {key: values[index] for key, values in ROWS.items()}

def current_memberships(language):
    labels = member_vocabulary(language)[1]
    moment = timezone.now()
    rows = []
    for tier in ("general", "affiliate", "advanced", "accredited"):
        price = Price.objects.filter(tier=tier, starts_at__lte=moment).order_by("-starts_at", "-pk").first()
        rows.append(dict(tier=tier, name=labels[tier], amount=price.amount if price else None,
                         featured=tier == "accredited"))
    return rows
