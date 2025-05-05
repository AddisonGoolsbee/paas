# PAAS

*This is a mirror. See upstream: <https://github.com/birdflop/pass>*

Birdflop service for free educational server usage. Called PaaS for no particular reason, started as Python-as-a-Service but now it's just kind of everything. Like Google Colab but way more basic.

## Development

### Frontend

- `cd frontend`
- `npm i` to install dependencies
- `npm run dev`

### Backend

- Make sure you have `Docker` installed and running.
- `python -m venv .venv && source .venv/bin/activate && pip install -r backend/requirements.txt` to setup and install dependencies
- `python -m backend` to run the backend 