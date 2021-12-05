venv:
	python -m venv .venv
	.venv/bin/pip install -U pip

install: venv
	.venv/bin/pip install -r requirements.txt

extract:
	.venv/bin/scrapy crawl --overwrite-output=raw.json schools

transform:
	.venv/bin/python transform.py

transform-env:
	.venv/bin/dotenv run -- .venv/bin/python transform.py

clean:
	rm raw.json

serve:
	.venv/bin/python -m http.server --directory=website

tweet:
	.venv/bin/python tweet.py

tweet-env:
	.venv/bin/dotenv run -- .venv/bin/python tweet.py

pip-compile: venv
	.venv/bin/pip-compile --upgrade

.PHONY: $(MAKECMDGOALS)
