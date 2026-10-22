"""Public presentation copy only; no personal or private assessment data."""
from django.utils import timezone
from governance.models import Price
from governance.member_labels import vocabulary as member_vocabulary

ROWS = {
 "home": ("الرئيسية", "Accueil", "Home"),
 "founders": ("الأعضاء المؤسسون", "Membres fondateurs", "Founding members"),
 "founder_note": ("الرئيس ونائب الرئيس من الأعضاء المؤسسين أيضًا.", "Le président et le vice-président sont également membres fondateurs.", "The president and vice-president are also founding members."),
 "menu": ("القائمة", "Menu", "Menu"),

 "contact": ("تواصل معنا", "Nous contacter", "Contact us"),
 "contact_intro": ("للاستفسار عن الجمعية وبرامجها والعضوية والشراكات، تواصل معنا عبر الوسيلة المناسبة لك.", "Pour toute information sur l’association, ses programmes, les adhésions ou les partenariats, choisissez le moyen de contact qui vous convient.", "For information about the association, programmes, membership or partnerships, choose the contact method that suits you."),
 "contact_phone": ("الهاتف وواتساب", "Téléphone et WhatsApp", "Phone and WhatsApp"),
 "contact_call": ("اتصل بنا", "Nous appeler", "Call us"),
 "contact_whatsapp": ("تواصل عبر واتساب", "Écrire sur WhatsApp", "Contact on WhatsApp"),
 "contact_address": ("العنوان", "Adresse", "Address"),
 "contact_email": ("البريد الإلكتروني الرسمي للجمعية", "Adresse électronique officielle de l’association", "Official association email"),

 "synthetic_notice": ("معاينة محلية ببيانات اصطناعية فقط؛ البرامج والخدمات المعروضة للتعريف، وليست إعلانًا عن إطلاق رسمي.", "Aperçu local avec données fictives uniquement. Les programmes et services sont présentés à titre informatif, sans lancement officiel.", "Local preview with synthetic data only. Programmes and services are informational and do not announce an official launch."),
 "mission_title": ("المعرفة والمواكبة وجودة الممارسة", "Connaissance, accompagnement et qualité des pratiques", "Knowledge, support and quality practice"),
 "mission_intro": ("تجمع ANTHEC المهنيين والمهتمين حول العلاج النفسي والأسري والكوتشينغ، للتعريف بهذه المجالات، وتبادل الخبرات، وتشجيع الممارسة المسؤولة والتعاون.", "ANTHEC réunit professionnels et personnes intéressées par la psychothérapie, la thérapie familiale et le coaching pour partager les connaissances et encourager des pratiques responsables et la coopération.", "ANTHEC brings together professionals and people interested in psychotherapy, family therapy and coaching to share knowledge and encourage responsible practice and cooperation."),
 "mission": ("رسالتنا", "Notre mission", "Our mission"),
 "mission_text": ("تقريب المعرفة النفسية والأسرية من المجتمع، ودعم تطوير كفاءات المهنيين، ضمن إطار جمعوي يحترم الإنسان والخصوصية وحدود الاختصاص.", "Rendre les connaissances psychologiques et familiales plus accessibles et soutenir les compétences professionnelles dans un cadre associatif respectueux des personnes, de la confidentialité et des limites de compétence.", "Make psychological and family knowledge more accessible and support professional development within an association that respects people, privacy and scope of competence."),
 "goals": ("أهدافنا", "Nos objectifs", "Our goals"),
 "goal_knowledge": ("نشر الوعي والمعرفة الموثوقة", "Diffuser des connaissances et sensibiliser", "Share knowledge and build awareness"),
 "goal_skills": ("تطوير الكفاءات وتبادل الخبرات", "Développer les compétences et partager les expériences", "Develop skills and exchange experience"),
 "goal_cooperation": ("تشجيع التعاون والممارسة المسؤولة", "Encourager la coopération et les pratiques responsables", "Encourage cooperation and responsible practice"),
 "services": ("مجالات العمل والخدمات", "Domaines d’action et services", "Areas of work and services"),
 "services_intro": ("مساران متكاملان: معرفة ومواكبة للمستفيدين، وتطوير وتعاون للمهنيين. تُحدد الخدمات المتاحة وشروطها في البرامج والأنشطة المعتمدة.", "Deux parcours complémentaires : information et accompagnement des bénéficiaires, développement et coopération des professionnels. Les services disponibles et leurs conditions sont précisés dans les programmes approuvés.", "Two complementary pathways: information and support for beneficiaries, development and cooperation for professionals. Available services and conditions are specified in approved programmes."),
 "beneficiaries": ("للمستفيدين والأسر", "Pour les bénéficiaires et les familles", "For beneficiaries and families"),
 "beneficiary_intro": ("فهم أفضل للصحة النفسية والعلاقات الأسرية، والتعرف على مسارات المواكبة المناسبة.", "Mieux comprendre la santé psychologique et les relations familiales, et découvrir les parcours d’accompagnement adaptés.", "Understand psychological wellbeing and family relationships, and explore suitable support pathways."),
 "beneficiary_awareness": ("لقاءات ومواد للتوعية والتثقيف النفسي والأسري", "Rencontres et ressources de sensibilisation psychologique et familiale", "Psychological and family awareness sessions and resources"),
 "beneficiary_guidance": ("التعريف بمجالات التدخل وحدودها ومسارات التوجيه", "Information sur les domaines d’intervention, leurs limites et les possibilités d’orientation", "Information about areas of practice, their limits and guidance pathways"),
 "beneficiary_activities": ("أنشطة وورشات وفق البرامج والشروط المعلنة", "Activités et ateliers selon les programmes et conditions annoncés", "Activities and workshops under announced programmes and conditions"),
 "professionals": ("للمهنيين والطلبة", "Pour les professionnels et les étudiants", "For professionals and students"),
 "professional_intro": ("فضاء لتطوير الممارسة والتعلم المستمر وبناء علاقات مهنية مسؤولة.", "Un espace de développement des pratiques, d’apprentissage continu et de coopération professionnelle responsable.", "A space to develop practice, continue learning and build responsible professional relationships."),
 "professional_learning": ("لقاءات علمية وتبادل الخبرات والتطوير المستمر", "Rencontres scientifiques, échanges d’expériences et développement continu", "Scientific meetings, experience sharing and continuing development"),
 "professional_membership": ("مسارات عضوية واضحة ومشاركة في الأنشطة", "Parcours d’adhésion clairs et participation aux activités", "Clear membership pathways and participation in activities"),
 "professional_quality": ("اعتماد جمعوي وفق المراجعة والقرار المعتمد", "Accréditation associative selon examen et décision approuvée", "Association accreditation following review and an approved decision"),
 "structure": ("هيكلة الجمعية", "Organisation de l’association", "Association structure"),
 "structure_intro": ("تعرف على رئاسة الجمعية والمجلس المؤسس. تُنشر الأسماء والصفات المعتمدة ضمن المحتوى المؤسسي.", "Découvrez la présidence et le conseil fondateur. Les noms et fonctions approuvés sont publiés dans le contenu institutionnel.", "Meet the presidency and founding council. Approved names and roles are published as institutional content."),
 "president": ("رئيس الجمعية", "Président de l’association", "Association president"),
 "vice_president": ("نائب الرئيس", "Vice-président", "Vice-president"),
 "founding_council": ("أعضاء المجلس المؤسس", "Membres du conseil fondateur", "Founding council members"),
 "names_pending": ("تُضاف الأسماء بعد اعتماد قائمة النشر.", "Les noms seront ajoutés après approbation de la liste à publier.", "Names will be added after the publication list is approved."),
 "discover_services": ("اكتشف مجالات عملنا", "Découvrir nos domaines d’action", "Explore our areas of work"),
}
ROWS.update({
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
 "hero": ("معًا نحو وعي أعمق وممارسة مسؤولة", "Ensemble pour mieux comprendre et mieux accompagner", "Together for understanding and responsible practice"),
 "intro": ("جمعية تجمع المعرفة النفسية والأسرية والتطوير المهني؛ فضاء للمستفيدين والأسر والمهنيين للتعلم والمشاركة والتعاون.", "Une association dédiée aux connaissances psychologiques et familiales et au développement professionnel : un espace pour apprendre, participer et coopérer.", "An association bringing psychological and family knowledge together with professional development: a space for beneficiaries, families and professionals to learn, participate and cooperate."),
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
})
def vocabulary(language):
    language = language if language in ("ar", "fr", "en") else "ar"
    index = ("ar", "fr", "en").index(language)
    result = {key: values[index] for key, values in ROWS.items()}
    from django.conf import settings
    if getattr(settings, "ANTHEEC_OPERATIONAL", False):
        result["privacy_detail"] = (
            "بيانات الطلبات والتقييمات داخلية. التحقق من الوثائق بمرجعها ورمزها أو QR، دون بحث بالأسماء.",
            "Demandes et évaluations restent privées. Vérification par référence et code ou QR, sans recherche par nom.",
            "Applications and assessments remain private. Verify documents by reference and code or QR, without name search.",
        )[index]
    return result

def current_memberships(language):
    labels = member_vocabulary(language)[1]
    moment = timezone.now()
    rows = []
    for tier in ("general", "affiliate", "advanced", "accredited"):
        price = Price.objects.filter(tier=tier, starts_at__lte=moment).order_by("-starts_at", "-pk").first()
        rows.append(dict(tier=tier, name=labels[tier], amount=price.amount if price else None,
                         featured=tier == "accredited"))
    return rows
