from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("orders", "0002_order_inventory_deducted")]

    operations = [
        migrations.AlterField(
            model_name="order",
            name="payment_status",
            field=models.CharField(
                choices=[
                    ("pending", "Pending"), ("paid", "Paid"),
                    ("failed", "Failed"), ("refund_pending", "Refund pending"),
                    ("refunded", "Refunded"),
                ], default="pending", max_length=20,
            ),
        ),
        migrations.CreateModel(
            name="RazorpayPaymentEvent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("event_id", models.CharField(blank=True, max_length=128, null=True, unique=True)),
                ("payment_id", models.CharField(max_length=100, unique=True)),
                ("refund_required", models.BooleanField(default=False)),
                ("refund_id", models.CharField(blank=True, max_length=100)),
                ("refund_processed", models.BooleanField(default=False)),
                ("refund_attempted_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("order", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="payment_events", to="orders.order")),
            ],
        ),
    ]
