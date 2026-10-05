MODEL ?= qwen3:8b

.PHONY: test index run ui eval eval-retrieval compare-models

test:
	pytest -q

index:
	trustdesk index sample_data/policies --library sample_data/past_questionnaires/2025_customer_questionnaire.csv

run:
	trustdesk run sample_data/questionnaires/acme_bank_2026.xlsx --model $(MODEL)

ui:
	streamlit run src/trustdesk/app.py

eval-retrieval:
	for m in keyword vector hybrid; do trustdesk eval sample_data/eval/questions.jsonl --retrieval-only --mode $$m --tag retrieval_$$m; done

eval:
	trustdesk eval sample_data/eval/questions.jsonl --model $(MODEL)

compare-models:
	trustdesk eval sample_data/eval/questions.jsonl --model qwen3:8b --tag qwen3-8b
	ollama stop qwen3:8b || true
	trustdesk eval sample_data/eval/questions.jsonl --model gemma4 --tag gemma4
