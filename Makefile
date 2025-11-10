.PHONY: typecheck

MYPY_MODULES=backend/nutribot \
backend/apps/common/renderers.py \
backend/apps/feed/adapters/rss.py \
backend/apps/feed/events.py \
backend/apps/catalog/etl/usda.py

typecheck:
	PYTHONPATH=backend DJANGO_DEBUG=1 DJANGO_SECRET_KEY=dev-secret mypy $(MYPY_MODULES)
