"""Versioned notice and acknowledgement evidence; activation is a separate decision."""
import hashlib
import json
from datetime import date
from django import forms
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.utils import timezone
from django.utils.html import format_html
from django.utils.translation import get_language

VERSION = 'ANTHEC-privacy-v2-20261022'
WORDS = {
 'ar': ('إشعار الخصوصية', 'اطلعت على إشعار الخصوصية وفهمت أغراض المعالجة ووسائل ممارسة حقوقي.', 'قراءة الإشعار', [
  ('المسؤول والتواصل', 'تدير الجمعية الوطنية للعلاج النفسي والأسري والكوتشينغ ANTHEC، ممثلة في رئيسها الدكتور إدريس هلالي، معالجة بيانات المنصة. توجه طلبات الخصوصية كتابة إلى الرئيس: رقم 43، زنقة أكلمام سيدي علي، أكدال، الرباط، أو عبر واتساب 0663400190. لا ترسل كلمات المرور أو رموز الدخول أو مفاتيح التشفير.'),
  ('البيانات والأغراض', 'بحسب الخدمة، تعالج بيانات الحساب والاسم والتواصل والمهنة والصفة والعنوان المناسب والصورة، والطلبات والقرارات والأداء والوثائق، وبيانات الولي عند مشاركة قاصر. الغرض فحص الطلب وتنظيم العلاقة والأنشطة والشراكات وإصدار الوثائق وتتبع صلاحيتها وحماية الحساب. لا ترسل ملفات علاجية أو تشخيصات أو بيانات صحية في الحقول الحرة. الحقول اللازمة موضحة بالنموذج؛ نقصها يمنع إتمام الخدمة المعنية. إنشاء الحساب أو الأداء لا يعوض الموافقة الإدارية.'),
  ('الاطلاع والصورة والتحقق', 'يطلع الرئيس والمفوضون في نطاق صلاحياتهم وصاحب الحساب على السجلات المرتبطة به. الصورة للطلب والبطاقة وليست إذنًا بالإشهار. يتيح QR أو مرجع الوثيقة ورمزها الاطلاع على الاسم والنوع والمرجع والصلاحية والحالة، دون الصورة أو الهاتف أو العنوان أو الأسباب الداخلية. مشاركة الرمز قد تتيح التحقق للغير. لا بحث عام بالأسماء ولا دليل أعضاء عام تلقائي. إقرار الاطلاع مستقل عن موافقة الصورة وإشعار التحقق وموافقة الولي وأي نشر اختياري.'),
  ('الاستضافة والخدمات', 'تستخدم الخدمة وقاعدة البيانات Render بمنطقة فرانكفورت؛ لا يفترض انحصار جميع عمليات الدعم والنسخ والمقاولين الفرعيين في المنطقة نفسها. لا ترسل بيانات الطلبات الخاصة إلى خدمة الترجمة؛ تقتصر الترجمة الاختيارية على محتوى الأنشطة العام. البريد الآلي والتسويق والدليل العام ليست خدمات مفعلة بموجب هذا الإشعار. إجراءات المعالجة والنقل ومراجعها النظامية تحتاج استكمالًا وإثباتًا؛ لا يمثل الإشعار ترخيصًا أو شهادة امتثال.'),
  ('الحفظ والحقوق والقاصرون', 'يخضع الحفظ لضرورة الغرض وجدول الجمعية والاستثناءات المالية أو النزاع الموثقة، مع فصل الأرشيف والنسخ الاحتياطية عن التشغيل. يمكن طلب الولوج والتصحيح والاعتراض وفحص الحذف عبر قناة الرئيس، مع تحقق متناسب من الهوية والرد على النتيجة أو سبب الاستثناء. لا وعد بحذف فوري شامل للأرشيف المالي والنسخ؛ يلزم إعادة تطبيق قرارات الحذف عند الاستعادة. يقدم الولي أو الممثل القانوني مشاركة القاصر بموافقة صريحة ومراجعة شروط النشاط. لا يعد ذلك إذنًا بالعلاج أو نشر صورة القاصر.'),
  ('ملفات الارتباط والإقرار', 'تستخدم ملفات الجلسة وحماية الطلبات لتشغيل الدخول والأمان. لا يتضمن هذا الإقرار موافقة تسويق أو تتبع اختياري. تحفظ هوية الحساب عند وجوده، والغرض ورقم النص ولغته ونسخته الكاملة وبصمته وتوقيت الإقرار. لا تضاف بيانات IP أو بصمة جهاز لهذا الإثبات. لا ينشئ الاطلاع عضوية أو اعتمادًا ولا يعوض الإجراءات النظامية المطلوبة.')]),
 'fr': ('Notice de confidentialité', 'J’ai lu la notice de confidentialité et compris les finalités du traitement et les moyens d’exercer mes droits.', 'Lire la notice', [
  ('Responsable et contact', 'L’association ANTHEC, représentée par son président Driss Helali, est responsable des traitements de la plateforme. Les demandes écrites relatives à la confidentialité sont adressées au président : 43, rue Aguelmane Sidi Ali, Agdal, Rabat, ou par WhatsApp au 0663400190. Ne transmettez ni mots de passe, ni codes de connexion, ni clés de chiffrement.'),
  ('Données et finalités', 'Selon le service, les données comprennent compte, identité, coordonnées, profession, qualité déclarée, adresse pertinente, portrait, demandes, décisions, paiements et documents, ainsi que les données du représentant légal pour un mineur. Elles servent à examiner les demandes, gérer la relation, les activités et partenariats, émettre les documents, suivre leur validité et protéger les comptes. Ne saisissez aucun dossier thérapeutique, diagnostic ou renseignement de santé dans les champs libres. Les champs nécessaires sont indiqués ; leur absence empêche le service concerné. Un compte ou un paiement ne remplace pas la décision administrative.'),
  ('Accès, portrait et vérification', 'Le président et les délégataires accèdent aux données selon leurs droits ; le titulaire accède à ses propres dossiers. Le portrait sert au dossier et à la carte, sans autorisation publicitaire. Le QR ou la référence et le code du document donnent accès au nom, au type, à la référence, aux dates et au statut, sans portrait, coordonnées ni motifs internes. Partager le code peut permettre une vérification par un tiers. Il n’existe ni recherche publique par nom ni annuaire automatique des membres. L’accusé de lecture reste distinct des consentements au portrait, à la vérification, du représentant légal et de toute publication facultative.'),
  ('Hébergement et prestataires', 'Le service et la base sont hébergés chez Render à Francfort ; cela ne signifie pas que toutes les opérations de support, de sauvegarde et des sous-traitants se limitent à cette région. Aucune donnée privée de demande n’est envoyée au service de traduction ; la traduction facultative concerne les textes publics des activités. Cette notice n’active ni courriel automatisé, ni marketing, ni annuaire public. Les formalités applicables aux traitements et transferts et leurs références restent à compléter et à justifier ; cette notice n’est ni une autorisation ni un certificat de conformité.'),
  ('Conservation, droits et mineurs', 'La conservation dépend de la finalité, du calendrier de l’association et des exceptions financières ou contentieuses documentées ; archives et sauvegardes sont séparées de l’exploitation. Les demandes d’accès, rectification, opposition ou examen d’effacement sont adressées au président, avec vérification proportionnée de l’identité et réponse motivée. Aucun effacement immédiat de toutes les archives financières ou sauvegardes n’est promis ; les décisions d’effacement doivent être réappliquées après restauration. La participation d’un mineur est soumise à la demande et au consentement explicite du représentant légal et aux conditions de l’activité, sans autorisation de soins ou de publication du portrait.'),
  ('Cookies et preuve de lecture', 'Les cookies de session et de protection des requêtes servent à la connexion et à la sécurité. Cet accusé n’autorise ni marketing ni suivi facultatif. La preuve conserve le compte lorsqu’il existe, la finalité, l’identifiant du texte, sa langue, son contenu complet, son empreinte et la date de lecture. Aucune adresse IP ni empreinte d’appareil n’est ajoutée à cette preuve. La lecture ne crée ni adhésion ni accréditation et ne remplace aucune formalité applicable.')]),
 'en': ('Privacy notice', 'I have read the privacy notice and understood the processing purposes and how to exercise my rights.', 'Read the notice', [
  ('Controller and contact', 'ANTHEC, represented by its president Driss Helali, is responsible for platform processing. Send written privacy requests to the president at 43, rue Aguelmane Sidi Ali, Agdal, Rabat, or WhatsApp 0663400190. Do not send passwords, login codes or encryption keys.'),
  ('Data and purposes', 'Depending on the service, data include account, name, contact details, profession, declared capacity, relevant address, portrait, applications, decisions, payments and documents, and legal representative details for a minor. Purposes include reviewing requests, managing the relationship, activities and partnerships, issuing documents, tracking validity and protecting accounts. Do not enter therapy files, diagnoses or health details in free text. Required fields are identified; missing them prevents the relevant service. An account or payment does not replace administrative approval.'),
  ('Access, portraits and verification', 'The president and delegates have access within their permissions; account holders see their own linked records. Portraits serve the application and card and do not authorize advertising. A QR or document reference and code expose name, type, reference, dates and status, without portrait, contacts or internal reasons. Sharing the code may allow a third party to verify the document. There is no public name search or automatic member directory. Reading acknowledgement remains separate from portrait consent, verification notice, guardian consent and optional publication.'),
  ('Hosting and services', 'The service and database use Render in Frankfurt; this does not imply that all support, backups and subprocessor operations stay in that region. Private application data are not sent to translation services; optional translation concerns public activity copy. This notice does not activate automated email, marketing or a public directory. Applicable processing and transfer formalities and their references still need completion and evidence; this notice is not an authorization or compliance certificate.'),
  ('Retention, rights and minors', 'Retention follows purpose, the association’s schedule and documented financial or dispute exceptions, with archives and backups separated from live use. Access, correction, objection and erasure review requests go to the president, with proportionate identity checks and a reasoned response. Immediate erasure of all financial archives or backups is not promised; erasure decisions must be reapplied after restoration. A minor’s participation requires a legal representative’s request and explicit consent and review of activity conditions, without authorizing treatment or publication of the minor’s portrait.'),
  ('Cookies and acknowledgement evidence', 'Session and request protection cookies support login and security. This acknowledgement does not authorize marketing or optional tracking. Evidence records the account where present, purpose, text identifier, language, complete text, digest and acknowledgement time. No IP address or device fingerprint is added to this evidence. Reading does not create membership or accreditation or replace any applicable formality.')]),
}


def enabled():
    if not getattr(settings, 'ANTHEEC_PRIVACY_NOTICE_ENABLED', False):
        return False
    try:
        day = date.fromisoformat(settings.ANTHEEC_PRIVACY_NOTICE_PUBLISHED_ON)
        if day.isoformat() != settings.ANTHEEC_PRIVACY_NOTICE_PUBLISHED_ON or day > timezone.localdate():
            raise ValueError
    except (AttributeError, ValueError, TypeError):
        raise ImproperlyConfigured('Privacy notice requires an explicit ISO publication date.') from None
    return True


def snapshot(language):
    if language not in WORDS:
        raise ValidationError('Unsupported privacy language')
    if not enabled():
        raise ValidationError('Privacy notice is not activated')
    title, acknowledgement, link, sections = WORDS[language]
    content = {'version': VERSION, 'published_on': settings.ANTHEEC_PRIVACY_NOTICE_PUBLISHED_ON,
               'language': language, 'title': title, 'acknowledgement': acknowledgement,
               'sections': sections}
    content['sha256'] = hashlib.sha256(json.dumps(content, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
    return content


def pop_ack(data):
    accepted = data.pop('privacy_acceptance', False)
    version = data.pop('privacy_version', '')
    language = data.pop('privacy_language', '')
    if not enabled():
        return None
    if accepted is not True or version != VERSION:
        raise ValidationError('Current privacy notice acknowledgement required')
    return snapshot(language)


def record(user, purpose, subject, evidence):
    if evidence is not None:
        from .services import audit
        audit(user, 'privacy.acknowledged', f'{purpose}:{subject}', purpose=purpose, notice=evidence)


class PrivacyNoticeMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if enabled():
            language = (get_language() or 'ar').split('-')[0]
            language = language if language in WORDS else 'ar'
            title, text, link, _ = WORDS[language]
            self.fields['privacy_acceptance'] = forms.BooleanField(label=text, required=True,
                help_text=format_html('<a href="/privacy/?lang={}" target="_blank" rel="noopener">{}</a> · {}', language, link, VERSION))
            self.fields['privacy_version'] = forms.CharField(initial=VERSION, widget=forms.HiddenInput)
            self.fields['privacy_language'] = forms.ChoiceField(choices=[(language, language)], initial=language, widget=forms.HiddenInput)

    def clean(self):
        data = super().clean()
        if enabled() and data.get('privacy_version') != VERSION:
            self.add_error('privacy_version', 'Current privacy notice required.')
        return data
