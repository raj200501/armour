.PHONY: test compile dataset live-external model-dry-run model-claim-candidates judge-comparison outcome-state secrets clean

test:
	python3 -m unittest discover -s tests

compile:
	python3 -m compileall -q armour_labs scripts tests

dataset:
	python3 scripts/generate_labeled_dataset.py
	python3 scripts/generate_benchmark_v1.py

live-external:
	python3 scripts/run_live_external_agent_benchmark.py
	python3 scripts/generate_benchmark_v3.py

model-dry-run:
	python3 scripts/run_model_agent_benchmark.py --dry-run --provider gemini --model dry-run-gemini --limit 2
	python3 scripts/run_model_judge_baseline.py datasets/live_external_agent_runs.jsonl --dry-run --provider gemini --model dry-run-gemini
	python3 scripts/generate_benchmark_v4.py

model-claim-candidates:
	python3 scripts/generate_model_claim_candidates.py

judge-comparison:
	python3 scripts/generate_model_claim_judge_comparison.py

outcome-state:
	python3 scripts/generate_outcome_state_report.py

secrets:
	python3 scripts/check_no_secrets.py

clean:
	rm -rf __pycache__ armour_labs/__pycache__ tests/__pycache__ scripts/__pycache__
