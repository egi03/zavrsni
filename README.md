```bash
pip install -r requirements.txt
```

```bash
python manage.py migrate
```

```bash
python manage.py runserver
```

## Management (optional)

### Last.fm songs enrichment
```bash
python manage.py enrich_songs_lastfm
```

### Model Training
```bash
python manage.py train_recommendations --model collaborative
```

### Update Recommendations
```bash
python manage.py update_recommendations
```
