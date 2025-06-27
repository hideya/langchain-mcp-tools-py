# NOTES: 
# - The command lines (recipe lines) must start with a TAB character.
# - Each command line runs in a separate shell without .ONESHELL:
.PHONY: clean install build check-pkg prep-publish test-publish publish \
		test run-example sphinx gh-pages
.ONESHELL:

.venv:
	uv venv

install: .venv
	uv pip install -e .

build: clean install
	uv build
	@echo
	uvx twine check dist/*

check-pkg:
	uv pip show -f langchain-mcp-tools

prep-publish: build
	# set PYPI_API_KEY from .env
	$(eval export $(shell grep '^PYPI_API_KEY=' .env ))

	# check if PYPI_API_KEY is set
	@if [ -z "$$PYPI_API_KEY" ]; then \
		echo "Error: PYPI_API_KEY environment variable is not set"; \
		exit 1; \
	fi

publish: prep-publish
	uvx twine upload \
		--verbose \
		--repository-url https://upload.pypi.org/legacy/ dist/* \
		--password ${PYPI_API_KEY}

test-publish: prep-publish
	tar tzf dist/*.tar.gz
	@echo
	unzip -l dist/*.whl
	@echo
	uvx twine check dist/*

install-dev: install
	uv pip install -e ".[dev]"

test: install-dev
	.venv/bin/pytest tests/ -v

run-simple-usage: install-dev
	uv run testfiles/simple_usage.py

# E.g.: make run-streamable-http-oauth-test-server
run-%-test-server: install-dev
	uv run testfiles/$(shell echo $* | tr '-' '_')_test_server.py

# E.g.: make run-streamable-http-oauth-test-client
run-%-test-client: install-dev
	uv run testfiles/$(shell echo $* | tr '-' '_')_test_client.py

sphinx: install
	make -C docs clean html

deploy-docs: sphinx
	ghp-import -n -p -f docs/_build/html

clean:
	git clean -fdxn -e .env
	@read -p 'OK?'
	git clean -fdx -e .env
