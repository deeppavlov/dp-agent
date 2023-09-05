.PHONY: check_format format lint type_check check_code unit_test

check_format:
	black deeppavlov_agent/ --diff --check

format:
	black deeppavlov_agent/

lint: 
	flake8 deeppavlov_agent/ --count --show-source --statistics

type_check:
	mypy deeppavlov_agent/

check_code: check_format lint type_check

unit_test:
	pytest deeppavlov_agent/tests
