from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('products', '0001_initial'),
        ('stores', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Ingredient',
            fields=[
                ('id',            models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True)),
                ('created_at',    models.DateTimeField(auto_now_add=True)),
                ('updated_at',    models.DateTimeField(auto_now=True)),
                ('name',          models.CharField(max_length=200)),
                ('unit',          models.CharField(max_length=10, choices=[('kg','Kilogram (kg)'),('g','Gram (g)'),('l','Litre (L)'),('ml','Millilitre (mL)'),('piece','Piece / Unit'),('dozen','Dozen')], default='piece')),
                ('current_stock', models.DecimalField(max_digits=12, decimal_places=3, default=0)),
                ('reorder_level', models.DecimalField(max_digits=12, decimal_places=3, default=0)),
                ('cost_per_unit', models.DecimalField(max_digits=10, decimal_places=2, default=0)),
                ('notes',         models.TextField(blank=True)),
                ('store',         models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='ingredients', to='stores.store')),
            ],
            options={'db_table': 'rest_ingredients', 'ordering': ['name'], 'unique_together': {('store', 'name')}},
        ),
        migrations.CreateModel(
            name='Recipe',
            fields=[
                ('id',         models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('name',       models.CharField(max_length=200)),
                ('serves',     models.PositiveIntegerField(default=1)),
                ('notes',      models.TextField(blank=True)),
                ('store',      models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='recipes', to='stores.store')),
                ('product',    models.OneToOneField(null=True, blank=True, on_delete=django.db.models.deletion.CASCADE, related_name='recipe', to='products.product')),
            ],
            options={'db_table': 'rest_recipes', 'ordering': ['name']},
        ),
        migrations.CreateModel(
            name='RecipeIngredient',
            fields=[
                ('id',                   models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True)),
                ('created_at',           models.DateTimeField(auto_now_add=True)),
                ('updated_at',           models.DateTimeField(auto_now=True)),
                ('quantity_per_serving', models.DecimalField(max_digits=10, decimal_places=3)),
                ('recipe',               models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='ingredients', to='restaurant.recipe')),
                ('ingredient',           models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='used_in_recipes', to='restaurant.ingredient')),
            ],
            options={'db_table': 'rest_recipe_ingredients', 'unique_together': {('recipe', 'ingredient')}},
        ),
        migrations.CreateModel(
            name='RestaurantWastage',
            fields=[
                ('id',          models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True)),
                ('created_at',  models.DateTimeField(auto_now_add=True)),
                ('updated_at',  models.DateTimeField(auto_now=True)),
                ('quantity',    models.DecimalField(max_digits=12, decimal_places=3)),
                ('reason',      models.CharField(max_length=20, choices=[('spoiled','Spoiled / Expired'),('prep_waste','Prep Waste (peeling/cutting)'),('overproduced','Overproduction'),('spillage','Spillage'),('other','Other')], default='other')),
                ('notes',       models.TextField(blank=True)),
                ('date',        models.DateField()),
                ('ingredient',  models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='wastage_records', to='restaurant.ingredient')),
                ('recorded_by', models.ForeignKey(null=True, blank=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
            options={'db_table': 'rest_wastage_records', 'ordering': ['-date', '-created_at']},
        ),
        migrations.CreateModel(
            name='DailyStock',
            fields=[
                ('id',            models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True)),
                ('created_at',    models.DateTimeField(auto_now_add=True)),
                ('updated_at',    models.DateTimeField(auto_now=True)),
                ('date',          models.DateField()),
                ('opening_stock', models.DecimalField(max_digits=12, decimal_places=3)),
                ('closing_stock', models.DecimalField(max_digits=12, decimal_places=3, null=True, blank=True)),
                ('received',      models.DecimalField(max_digits=12, decimal_places=3, default=0)),
                ('notes',         models.TextField(blank=True)),
                ('ingredient',    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='daily_stocks', to='restaurant.ingredient')),
                ('recorded_by',   models.ForeignKey(null=True, blank=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
            options={'db_table': 'rest_daily_stocks', 'ordering': ['-date'], 'unique_together': {('ingredient', 'date')}},
        ),
        migrations.AddIndex(
            model_name='ingredient',
            index=models.Index(fields=['store', 'name'], name='rest_ing_store_name_idx'),
        ),
        migrations.AddIndex(
            model_name='dailystock',
            index=models.Index(fields=['ingredient', 'date'], name='rest_ds_ing_date_idx'),
        ),
    ]
