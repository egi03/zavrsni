.PHONY: run test lint migrate seed shell clean train train-eval evaluate enrich

# ── Development ──────────────────────────────────────────────────────────────

run:
	python manage.py runserver

shell:
	python manage.py shell

# ── Database ──────────────────────────────────────────────────────────────────

migrate:
	python manage.py makemigrations
	python manage.py migrate

# ── Testing ───────────────────────────────────────────────────────────────────

test:
	python manage.py test recommendations.tests lastfm.tests spotify.tests social.tests music.tests

test-verbose:
	python manage.py test recommendations.tests lastfm.tests spotify.tests social.tests music.tests --verbosity=2

# ── Linting & formatting ──────────────────────────────────────────────────────

lint:
	ruff check .

lint-fix:
	ruff check . --fix

format:
	ruff format .

# ── ML pipeline ──────────────────────────────────────────────────────────────

train:
	python manage.py train_recommendations

train-eval:
	python manage.py evaluate_model --retrain

evaluate:
	python manage.py evaluate_model

enrich:
	python manage.py enrich_songs_lastfm

# ── Cleanup ───────────────────────────────────────────────────────────────────

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
