# Fixes RecommendationFeedback.recommendation to point to HybridRecommendation
# instead of PlaylistRecommendation. The views always use HybridRecommendation IDs
# so the old FK caused silent failures when recording feedback.

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('recommendations', '0002_recommendationfeedback_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='recommendationfeedback',
            name='recommendation',
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='feedback',
                to='recommendations.hybridrecommendation',
            ),
        ),
    ]
