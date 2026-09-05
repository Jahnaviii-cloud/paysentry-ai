.PHONY: test api web data model

test:
	python -m compileall backend ml
	pytest -q
	node --check frontend/app.js

api:
	uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000

web:
	cd frontend && python -m http.server 5173

data:
	python ml/generate_dataset.py

model:
	python ml/train_root_cause_model.py
