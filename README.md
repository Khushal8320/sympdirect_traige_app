# sympdirect_traige_app

SympDirect Triage App is an AI-based triage project that helps predict patient urgency level (KTAS score) using clinical and symptom data.

## Project Structure

```
sympdirect_traige_app/
├── data/                          # Raw and synthetic datasets
│   ├── emergency_traige1.csv
│   └── synthetic_data_updated_1.csv
├── notebooks/                     # Jupyter notebooks for exploration and modeling
│   ├── pycaret_emegency_traige.ipynb      # PyCaret AutoML model selection
│   ├── emergency_traiage_kp.ipynb         # Full ML pipeline (EDA + modeling)
│   ├── emergency_traiage_kp_trad.ipynb    # Traditional ML models
│   └── emergency_traiage_kp_deep.ipynb    # Deep learning models
├── models/                        # Trained model artifacts (.pkl)
│   ├── best_triage_model.pkl
│   ├── emergency_traige_pycaret_dt_model.pkl
│   └── emergency_traige_pycaret_rf_model.pkl
├── results/                       # Model evaluation outputs
│   ├── model_results.csv
│   └── threshold_tuned_predictions.csv
├── logs/                          # Training logs
│   └── logs.log
├── requirements.txt
└── .gitignore
```

## Setup

```bash
git clone https://github.com/Khushal8320/sympdirect_traige_app.git
cd sympdirect_traige_app
python -m venv env1
source env1/bin/activate    # On Windows: env1\Scripts\activate
pip install -r requirements.txt
```
