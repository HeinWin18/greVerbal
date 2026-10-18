# GRE Preparation Guide & Planner

An intentionally small GRE verbal preparation MVP for CS4800 Software Engineering.

## Stack
- Python + Flask
- MongoDB Atlas via PyMongo
- python-dotenv for local environment variables
- Gunicorn for production serving on EC2

## Current app
The homepage links to a vocabulary study page and an interactive verbal practice page. Both load
from MongoDB Atlas. Answer keys and explanations are returned only after a practice answer is
submitted. JSON endpoints are available at `/api/vocabulary` and `/api/verbal-questions`.

## macOS setup
1. Unzip this folder and open it in your editor.
2. In the project root, run:
   `chmod +x setup_venv_mac.sh`
   `./setup_venv_mac.sh`
3. Set `MONGODB_URI` and `MONGODB_DATABASE` in your local `.env` file. Keep `.env` private; it is
   ignored by Git. MongoDB TLS certificate verification uses the CA bundle provided by `certifi`.
4. Activate the environment in a new terminal with:
   `source .venv/bin/activate`
5. Seed the database from the project root:
   `python -m scripts.seed_data`
   This upserts the 10 vocabulary entries and 5 verbal questions by their stable word/question
   keys, so rerunning it does not create duplicates.
6. Start the app from the project root:
   `python wsgi.py`
7. Open `http://127.0.0.1:5000` and try **Study Vocabulary** and **Practice Verbal Questions**.

## Verify locally
Run `python -m unittest discover -v` for the route and answer-checking tests. The vocabulary page
is at `/vocabulary`; practice is at `/practice`. The JSON routes return the saved records without
exposing answer keys before submission.

## Verify data in Atlas
In MongoDB Atlas, select the database named by `MONGODB_DATABASE`, then open **Browse Collections**.
After a successful seed, it should contain `vocabulary` (10 documents) and `verbal_questions`
(5 documents). You can also check the app's `/api/vocabulary` and `/api/verbal-questions`
endpoints; each returns the saved records as JSON.

## Notes
- The `.venv` folder is generated on your machine and is intentionally not included in this ZIP.
- Do not commit `.env`, MongoDB credentials, AWS keys, or SSH private keys.
- Keep the MVP small: vocabulary reading and verbal question practice first.
