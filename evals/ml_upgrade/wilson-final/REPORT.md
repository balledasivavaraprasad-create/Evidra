# Model comparison

Dataset: SYNERGY-Appenzeller-Herzog_2020-abstract-screening

NOT_PROMOTED: independent benchmark/synthetic data is not validation for the active metformin review

Development-selected candidate: baseline-0; calibrated=False

| Candidate | Accuracy | Precision | Recall | F1 | AP | WSS@95 |
|---|---:|---:|---:|---:|---:|---:|
| baseline-0 | 0.8715 | 0.2838 | 0.9130 | 0.4330 | 0.6362 | 0.7304 |
| baseline-0-calibrated | 0.8715 | 0.2838 | 0.9130 | 0.4330 | 0.6362 | 0.7304 |
| logistic-1 | 0.8178 | 0.2222 | 0.9565 | 0.3607 | 0.5844 | 0.7748 |
| logistic-1-calibrated | 0.8178 | 0.2222 | 0.9565 | 0.3607 | 0.5844 | 0.7748 |
| xgboost-2 | 0.5818 | 0.1139 | 1.0000 | 0.2044 | 0.5803 | 0.6907 |
| xgboost-2-calibrated | 0.5818 | 0.1139 | 1.0000 | 0.2044 | 0.5803 | 0.6907 |
| xgboost-3 | 0.6402 | 0.1299 | 1.0000 | 0.2300 | 0.4540 | 0.7000 |
| xgboost-3-calibrated | 0.6402 | 0.1299 | 1.0000 | 0.2300 | 0.4540 | 0.7000 |
| catboost-4 | 0.8061 | 0.2059 | 0.9130 | 0.3360 | 0.5574 | 0.6813 |
| catboost-4-calibrated | 0.8061 | 0.2059 | 0.9130 | 0.3360 | 0.5574 | 0.6813 |
| catboost-5 | 0.4790 | 0.0935 | 1.0000 | 0.1710 | 0.4474 | 0.7210 |
| catboost-5-calibrated | 0.4790 | 0.0935 | 1.0000 | 0.1710 | 0.4474 | 0.7210 |
