from django.db import migrations, models


def close_legacy_grants(apps, schema_editor):
    Delegation = apps.get_model("governance", "Delegation")
    Group = apps.get_model("auth", "Group")
    alias = schema_editor.connection.alias
    for row in Delegation.objects.using(alias).all():
        row.active = False
        row.epoch += 1
        row.capabilities = []
        row.save(using=alias, update_fields=["active", "epoch", "capabilities"])
    # No implicit conversion of the historical broad CMS grant.
    legacy = (
        Group.objects.using(alias).filter(name="ANTHEEC operational directors").first()
    )
    if legacy:
        legacy.user_set.clear()
        legacy.permissions.clear()
        apps.get_model("wagtailcore", "GroupPagePermission").objects.using(
            alias
        ).filter(group_id=legacy.pk).delete()
        apps.get_model("wagtailcore", "GroupCollectionPermission").objects.using(
            alias
        ).filter(group_id=legacy.pk).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("governance", "0011_application_address_category_and_more"),
        ("wagtailcore", "0026_group_collection_permission"),
    ]
    operations = [
        migrations.AddField(
            model_name="delegation",
            name="capabilities",
            field=models.JSONField(blank=True, default=list),
        ),
        # Reversing the schema must never restore a broad authority grant.
        migrations.RunPython(close_legacy_grants, migrations.RunPython.noop),
    ]
