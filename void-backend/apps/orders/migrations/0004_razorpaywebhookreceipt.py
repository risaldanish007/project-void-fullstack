from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("orders", "0003_razorpay_payment_event_refund_pending")]

    operations = [
        migrations.CreateModel(
            name="RazorpayWebhookReceipt",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("event_id", models.CharField(max_length=128, unique=True)),
                ("event_type", models.CharField(max_length=80)),
                ("payment_id", models.CharField(blank=True, max_length=100)),
                ("received_at", models.DateTimeField(auto_now_add=True)),
            ],
        ),
    ]
