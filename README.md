# UK Solar Economics Calculator

An interactive Streamlit dashboard for modelling the economic benefits of residential solar PV + battery installations in the UK.

## Features

- **Weather-adjusted generation**: Compares theoretical peak output with realistic capacity-factor-adjusted generation
- **Battery modelling**: Simulates self-consumption with and without battery storage
- **Financial projections**: Multi-year cashflow, payback period, and NPV calculations
- **Interactive charts**: Visualise generation, consumption, and energy flows

## Run Locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Deploy on Streamlit Cloud

1. Fork this repository
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect your GitHub account
4. Select this repo and `app.py` as the main file
5. Click Deploy

## License

MIT
