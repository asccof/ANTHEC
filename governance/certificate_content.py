"""Owner wording mapped to recorded facts; no inferred criteria or speciality."""

from django.core.exceptions import ValidationError

CONTENT = {
    "professional_certificate": {
        "ar": ["تشهد الجمعية الوطنية للعلاج النفسي والأسري والكوتشينغ بأن السيد(ة):", "قد مُنح(ت) الاعتماد المهني الجمعوي وفق القرار المسجل لدى الجمعية، وفي حدود نوع الاعتماد المثبت في السجل.", "يُعد هذا الاعتماد اعترافًا مهنيًا صادرًا عن الجمعية، ولا يشكل ترخيصًا حكوميًا أو إذنًا قانونيًا بمزاولة مهنة منظمة."],
        "fr": ["L’Association Nationale de Thérapie Psychologique, Familiale et Coaching atteste que :", "a obtenu une accréditation professionnelle associative conformément à la décision enregistrée auprès de l’association, dans les limites du type d’accréditation consigné au registre.", "Cette accréditation constitue une reconnaissance professionnelle de l’association. Elle ne constitue ni une autorisation gouvernementale ni une autorisation légale d’exercer une profession réglementée."],
        "en": ["ANTHEC certifies that:", "has been granted association professional accreditation under the decision recorded by the association, within the limits of the accreditation type documented in the register.", "This accreditation is professional recognition issued by the association. It is neither a government licence nor legal authorization to practise a regulated profession."],
    },
    "accreditation_certificate": {
        "ar": ["تشهد الجمعية الوطنية للعلاج النفسي والأسري والكوتشينغ بأنها منحت:", "اعتمادًا جمعويًا من النوع المبين أدناه، وفق القرار المسجل لدى الجمعية، وخلال مدة الصلاحية المبينة في هذه الشهادة.", "لا يحل هذا الاعتماد محل التراخيص أو الموافقات التي قد تفرضها التشريعات الجاري بها العمل."],
        "fr": ["L’Association Nationale de Thérapie Psychologique, Familiale et Coaching atteste avoir accordé à :", "une accréditation associative du type indiqué ci-dessous, conformément à la décision enregistrée auprès de l’association, pour la période de validité précisée sur ce certificat.", "Cette accréditation ne remplace pas les autorisations ou agréments éventuellement exigés par la législation applicable."],
        "en": ["ANTHEC certifies that it has granted:", "association accreditation of the type shown below, under the decision recorded by the association and for the validity period stated on this certificate.", "This accreditation does not replace any licences or approvals that applicable legislation may require."],
    },
    "participation_design_proof": {
        "ar": ["تشهد الجمعية الوطنية للعلاج النفسي والأسري والكوتشينغ بأن:", "قد شارك(ت) في النشاط المذكور، الذي تنظمه الجهة المذكورة، خلال الفترة المبينة في هذا النموذج.", "تثبت هذه الشهادة المشاركة في النشاط المذكور، ولا تمنح بمفردها صفة مهنية أو ترخيصًا بالممارسة."],
        "fr": ["L’Association Nationale de Thérapie Psychologique, Familiale et Coaching atteste que :", "a participé à l’activité mentionnée, organisée par l’organisme mentionné, aux dates attestées dans cette maquette.", "Cette attestation confirme la participation à l’activité mentionnée. Elle ne confère à elle seule ni qualité professionnelle ni autorisation d’exercice."],
        "en": ["ANTHEC certifies that:", "participated in the stated activity, organized by the named organizer, on the dates documented in this design proof.", "This certificate confirms participation in the stated activity. It does not, by itself, confer professional status or a licence to practise."],
    },
}

TYPES = {
    "professional": ("اعتماد مهني جمعوي", "Accréditation professionnelle associative", "Association professional accreditation"),
    "individual": ("اعتماد جمعوي فردي", "Accréditation associative individuelle", "Individual association accreditation"),
    "institution": ("اعتماد جمعوي لمؤسسة", "Accréditation associative d’une institution", "Institutional association accreditation"),
    "course": ("اعتماد جمعوي لدورة أو برنامج تكويني", "Accréditation associative d’une formation ou d’un programme", "Association accreditation of a training course or programme"),
}


def scope(accreditation, language):
    if accreditation.kind not in TYPES:
        raise ValidationError("Recorded accreditation subtype required")
    # The current approved schema records a subtype and subject, not a precise
    # practice speciality or a structured finding that criteria were fulfilled.
    return TYPES[accreditation.kind][("ar", "fr", "en").index(language)]
