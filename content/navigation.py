"""One compact navigation, exclusively using published, public, menu-visible pages."""
GROUPS = [
    (("الجمعية", "L’association", "About us"), ("about", "vision", "goals", "fields", "governance", "ethics")),
    (("البرامج", "Programmes", "Programmes"), ("programmes", "training", "family-community")),
    (("العضوية", "Adhésion", "Membership"), ("membership", "accreditation")),
    (("الموارد والتعاون", "Ressources et coopération", "Resources and cooperation"), ("resources-news", "cooperation", "verification-guide", "faq")),
]


def navigation_groups(pages, language):
    pages = list(pages)
    by_slug = {p.slug: p for p in pages}
    index = {"ar": 0, "fr": 1, "en": 2}.get(language, 2)
    result = []
    assigned = {"contact"}
    for labels, slugs in GROUPS:
        items = [by_slug[s] for s in slugs if s in by_slug]
        assigned.update(slugs)
        if items:
            result.append(dict(label=labels[index], pages=items))
    # Newly created CMS pages remain discoverable without editing template code.
    extra = [p for p in pages if p.slug not in assigned]
    if extra:
        result.append(dict(label=("صفحات أخرى", "Autres pages", "Other pages")[index], pages=extra))
    return result
