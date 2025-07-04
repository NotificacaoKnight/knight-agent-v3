# Generated by Django 5.2.3 on 2025-06-24 03:34

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="ChatMessage",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "message_type",
                    models.CharField(
                        choices=[
                            ("user", "Usuário"),
                            ("assistant", "Assistente"),
                            ("system", "Sistema"),
                        ],
                        max_length=10,
                    ),
                ),
                ("content", models.TextField()),
                ("context_used", models.JSONField(blank=True, default=list)),
                ("search_query_id", models.IntegerField(blank=True, null=True)),
                ("llm_provider", models.CharField(blank=True, max_length=20)),
                ("llm_model", models.CharField(blank=True, max_length=50)),
                ("response_time_ms", models.IntegerField(blank=True, null=True)),
                ("is_helpful", models.BooleanField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "ordering": ["created_at"],
            },
        ),
        migrations.CreateModel(
            name="ChatFeedback",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "feedback_type",
                    models.CharField(
                        choices=[
                            ("helpful", "Útil"),
                            ("not_helpful", "Não Útil"),
                            ("incorrect", "Incorreto"),
                            ("incomplete", "Incompleto"),
                        ],
                        max_length=20,
                    ),
                ),
                ("comment", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "message",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="feedback",
                        to="chat.chatmessage",
                    ),
                ),
            ],
        ),
        migrations.CreateModel(
            name="ChatSession",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("title", models.CharField(blank=True, max_length=255)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("is_active", models.BooleanField(default=True)),
                ("message_count", models.IntegerField(default=0)),
                ("last_message_at", models.DateTimeField(blank=True, null=True)),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="chat_sessions",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["-updated_at"],
            },
        ),
        migrations.AddField(
            model_name="chatmessage",
            name="session",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="messages",
                to="chat.chatsession",
            ),
        ),
        migrations.CreateModel(
            name="DocumentRequest",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("document_name", models.CharField(max_length=255)),
                ("document_id", models.IntegerField(blank=True, null=True)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("requested", "Solicitado"),
                            ("found", "Encontrado"),
                            ("not_found", "Não Encontrado"),
                            ("downloaded", "Baixado"),
                        ],
                        default="requested",
                        max_length=20,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "message",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="document_requests",
                        to="chat.chatmessage",
                    ),
                ),
                (
                    "session",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="document_requests",
                        to="chat.chatsession",
                    ),
                ),
            ],
        ),
    ]
