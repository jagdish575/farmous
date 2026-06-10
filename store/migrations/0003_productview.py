import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("store", "0002_user_notification_preferences"),
    ]

    operations = [
        migrations.CreateModel(
            name="ProductView",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("session_key", models.CharField(db_index=True, max_length=40)),
                ("viewed_at", models.DateTimeField(default=django.utils.timezone.now)),
                (
                    "category",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="views",
                        to="store.category",
                    ),
                ),
                (
                    "medicine",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="views",
                        to="store.medicine",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="product_views",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["-viewed_at"],
                "indexes": [
                    models.Index(fields=["session_key", "viewed_at"], name="store_produ_session_6e8f2a_idx"),
                    models.Index(fields=["user", "viewed_at"], name="store_produ_user_id_8c4b1e_idx"),
                    models.Index(fields=["medicine", "viewed_at"], name="store_produ_medicin_2a9f3d_idx"),
                ],
            },
        ),
    ]
