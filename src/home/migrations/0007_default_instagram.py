from django.db import migrations

URL = "https://www.instagram.com/from.j2l/"


def fill_instagram(apps, schema_editor):
    SiteSettings = apps.get_model("home", "SiteSettings")
    SiteSettings.objects.filter(instagram_url="").update(instagram_url=URL)


class Migration(migrations.Migration):
    dependencies = [("home", "0006_alter_standardpage_body")]
    operations = [migrations.RunPython(fill_instagram, migrations.RunPython.noop)]
