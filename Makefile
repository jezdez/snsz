venv:
	python -m venv .venv
	.venv/bin/pip install -U pip

install: venv
	.venv/bin/pip install -r requirements.txt

extract:
	scrapy crawl --overwrite-output=raw.json schools

transform:
	python transform.py

clean:
	rm raw.json

serve:
	python -m http.server --directory=website

pip-compile:
	pip-compile --upgrade

.PHONY: $(MAKECMDGOALS)
