# EncryptionGuard — GitHub File Guide + Critical Fixes

---

## SECTION 1 — FILES TO COMMIT TO GITHUB

### Include everything EXCEPT what's in .gitignore

```
EncryptionGuard/
├── .gitignore                          ✅ COMMIT
├── Makefile                            ✅ COMMIT
├── README.md                           ✅ COMMIT
├── render.yaml                         ✅ COMMIT
├── .env.example                        ✅ COMMIT (no real values)
│
├── backend/
│   ├── app/
│   │   ├── main.py                     ✅ COMMIT
│   │   ├── config.py                   ✅ COMMIT
│   │   ├── models/                     ✅ COMMIT (all files)
│   │   ├── api/                        ✅ COMMIT (all files)
│   │   ├── services/                   ✅ COMMIT (all files)
│   │   └── workers/                    ✅ COMMIT (all files)
│   ├── features/
│   │   ├── schema.py                   ✅ COMMIT
│   │   ├── velocity.py                 ✅ COMMIT
│   │   ├── graph.py                    ✅ COMMIT
│   │   └── __init__.py                 ✅ COMMIT
│   ├── ml/
│   │   ├── train.py                    ✅ COMMIT
│   │   ├── evaluate.py                 ✅ COMMIT
│   │   ├── model_card.py               ✅ COMMIT
│   │   └── artifacts/
│   │       ├── metadata.json           ✅ COMMIT
│   │       ├── evaluation_results.json ✅ COMMIT
│   │       ├── MODEL_CARD.md           ✅ COMMIT
│   │       ├── pr_curve.png            ✅ COMMIT
│   │       ├── model.pkl               ❌ DO NOT COMMIT (binary, too large)
│   │       └── baseline_model.pkl      ❌ DO NOT COMMIT (binary, too large)
│   ├── data/
│   │   ├── generator.py                ✅ COMMIT
│   │   └── scenarios.py                ✅ COMMIT
│   ├── migrations/
│   │   └── 001_initial_schema.sql      ✅ COMMIT
│   ├── tests/
│   │   ├── conftest.py                 ✅ COMMIT
│   │   ├── test_webhook.py             ✅ COMMIT
│   │   ├── test_features.py            ✅ COMMIT
│   │   ├── test_split.py               ✅ COMMIT
│   │   ├── test_policy.py              ✅ COMMIT
│   │   └── fixtures/                   ✅ COMMIT (webhook JSON fixtures)
│   ├── requirements.txt                ✅ COMMIT
│   ├── railway.json                    ✅ COMMIT
│   └── .env.example                    ✅ COMMIT
│
├── frontend/
│   ├── src/                            ✅ COMMIT (all files)
│   ├── public/                         ✅ COMMIT
│   ├── package.json                    ✅ COMMIT
│   ├── vite.config.ts                  ✅ COMMIT
│   ├── tsconfig.json                   ✅ COMMIT
│   ├── tailwind.config.js              ✅ COMMIT
│   ├── vercel.json                     ✅ COMMIT
│   └── .env.example                    ✅ COMMIT
│
├── notebooks/
│   ├── 01_eda.ipynb                    ✅ COMMIT (with output cells visible)
│   ├── 02_feature_correlation.ipynb    ✅ COMMIT (with output cells visible)
│   ├── 03_pr_curves.ipynb              ✅ COMMIT (with output cells visible)
│   └── 04_shap_plots.ipynb             ✅ COMMIT (with output cells visible)
│
└── [these should NOT exist in your repo]
    ├── backend/init_db.py              ❌ DELETE and do not commit
    ├── backend/seed_db.py              ❌ DELETE and do not commit
    ├── backend/encryption_guard.db     ❌ DELETE and do not commit
    ├── backend/.env                    ❌ DELETE and do not commit
    └── frontend/.env                   ❌ DELETE and do not commit
```

---

## SECTION 2 — CRITICAL FIXES (do these before submission)

Fix in this exact order. Each fix depends on the previous one.

---

### FIX 1 — Supabase connection (do this today)

Your work report says: "tenant/user not found"

This is a URL format issue. Supabase has two connection strings. You are using the wrong one.

Go to: Supabase Dashboard → Project → Settings → Database → Connection string

Use the **Direct Connection** format, NOT the pooler:
```
postgresql://postgres:[YOUR-PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres
```

NOT the pooler URL which looks like:
```
postgresql://postgres.xxxx:[PASSWORD]@aws-0-ap-south-1.pooler.supabase.com:6543/postgres
```

The pooler requires a special user format. Use the direct connection for now.

After setting the correct URL:
1. Set `DATABASE_URL` in Render environment variables to the direct connection URL
2. Redeploy on Render
3. Run the SQL migration in Supabase SQL editor:
   ```
   Copy content of backend/migrations/001_initial_schema.sql → paste into Supabase SQL editor → Run
   ```
4. Verify tables were created: Supabase → Table Editor → you should see 12 tables

Once Supabase works, remove the SQLite fallback from `base.py`:
```python
# REMOVE this fallback logic entirely
DATABASE_URL = os.getenv("DATABASE_URL")  # Only Supabase, no fallback
```

---

### FIX 2 — Remove auto-seed from startup

Open `backend/app/main.py` and remove the `@app.on_event("startup")` handler that seeds 30 cases.

After Supabase is connected and the generator runs properly, data will come from `generator.py`.

```python
# DELETE this entire block from main.py
@app.on_event("startup")
async def startup_event():
    # ... seed 30 cases ...
```

---

### FIX 3 — Fix scenario labels in scenarios.py

Open `backend/data/scenarios.py` and fix the labels:

```python
# WRONG (current)
"shared_network": {"label": 1, "ring_id": None}

# CORRECT
"shared_network": {"label": 0, "ring_id": None}   # legitimate
"near_miss_shared_infra": {"label": 0, "ring_id": None}  # legitimate

# Abuse scenarios must have ring_id
"coordinated_ring":       {"label": 1, "ring_id": "RING_001"}
"coordinated_ring_large": {"label": 1, "ring_id": "RING_002"}
"high_loss_ring":         {"label": 1, "ring_id": "RING_003"}
"single_account_abuse":   {"label": 1, "ring_id": None}  # no ring needed for single
```

Correct label distribution should be:
- Label 0 (legitimate): normal_no_refund, legitimate_refund, shared_network, near_miss_shared_infra
- Label 1 (abuse): single_account_abuse, coordinated_ring, coordinated_ring_large, high_loss_ring

---

### FIX 4 — Fix generator seed not working

Open `backend/data/generator.py` and add this at the very top of the generate function:

```python
import random
import numpy as np

def generate(seed: int = 42, config: dict = None):
    random.seed(seed)
    np.random.seed(seed)
    # ... rest of generator
```

Verify it works:
```bash
python data/generator.py --seed 42  # save output count
python data/generator.py --seed 123 # must produce DIFFERENT output
python data/generator.py --seed 999 # must produce DIFFERENT output
```

If all three produce the same data, the seed is not being used for random decisions.

---

### FIX 5 — Fix prevalence (abuse rate must be 0.5–5%)

After fixing labels, your generator must produce a realistic abuse rate.
Target: approximately 2–5% abuse events for primary evaluation.

Control this by adjusting scenario frequency in the generator config:

```python
SCENARIO_WEIGHTS = {
    "normal_no_refund":          0.40,   # 40% of events
    "legitimate_refund":         0.30,   # 30%
    "shared_network":            0.15,   # 15% — legitimate
    "near_miss_shared_infra":    0.08,   # 8%  — legitimate
    "single_account_abuse":      0.03,   # 3%  — abuse
    "coordinated_ring":          0.02,   # 2%  — abuse
    "coordinated_ring_large":    0.01,   # 1%  — abuse
    "high_loss_ring":            0.01,   # 1%  — abuse
}
# Total abuse: 7%, legitimate: 93%
```

Target: generate at least 5,000 total events (not just 360 accounts).

---

### FIX 6 — Fix time-aware split

Open `backend/ml/train.py` and verify the split is time-based, not random:

```python
# CORRECT time-aware split
train = df[df["created_at"] < "2026-06-01"]
val   = df[(df["created_at"] >= "2026-06-01") & (df["created_at"] < "2026-08-01")]
test  = df[df["created_at"] >= "2026-08-01"]

# ALSO group-aware: remove ring_ids from test that appear in train
test_rings = set(test["ring_id"].dropna().unique())
train = train[~train["ring_id"].isin(test_rings)]
val   = val[~val["ring_id"].isin(test_rings)]
```

If you are currently using `train_test_split()` from sklearn, that is a random split and must be replaced.

---

### FIX 7 — Add ring-level metrics to evaluate.py

Add this function to `backend/ml/evaluate.py`:

```python
def evaluate_ring_level(df_test, y_proba, threshold):
    df = df_test.copy()
    df["y_pred"] = (y_proba >= threshold).astype(int)

    ground_truth_rings = set(df[df["event_label"] == 1]["ring_id"].dropna().unique())
    predicted_rings    = set(df[df["y_pred"] == 1]["ring_id"].dropna().unique())

    true_positives  = ground_truth_rings & predicted_rings
    false_positives = predicted_rings - ground_truth_rings
    false_negatives = ground_truth_rings - predicted_rings

    ring_precision = len(true_positives) / len(predicted_rings) if predicted_rings else 0
    ring_recall    = len(true_positives) / len(ground_truth_rings) if ground_truth_rings else 0
    ring_f1 = (2 * ring_precision * ring_recall /
               (ring_precision + ring_recall)) if (ring_precision + ring_recall) > 0 else 0

    return {
        "ring_precision": round(ring_precision, 4),
        "ring_recall": round(ring_recall, 4),
        "ring_f1": round(ring_f1, 4),
        "ground_truth_rings": len(ground_truth_rings),
        "predicted_rings": len(predicted_rings),
        "true_positive_rings": len(true_positives),
    }
```

This output must appear in `evaluation_results.json` and `MODEL_CARD.md`.

---

### FIX 8 — Connect Redis Cloud (velocity features)

In Render dashboard → Web Service → Environment Variables, add:
```
REDIS_URL = redis://default:[password]@[host]:[port]
```

Get this URL from Redis Cloud dashboard → Connect → copy the redis:// URL.

In `backend/features/velocity.py`, verify the connection:
```python
import redis, os

r = redis.from_url(os.getenv("REDIS_URL"))

def ping():
    return r.ping()  # Should return True
```

Add a health check in `main.py`:
```python
@app.get("/health")
async def health():
    redis_ok = False
    try:
        redis_ok = r.ping()
    except:
        pass
    return {"status": "healthy", "redis": redis_ok}
```

---

### FIX 9 — Connect Neo4j Aura (graph features)

In Render dashboard → Environment Variables, add:
```
NEO4J_URI      = neo4j+s://[your-aura-id].databases.neo4j.io
NEO4J_USERNAME = neo4j
NEO4J_PASSWORD = [your-aura-password]
```

Get these from Neo4j Aura → your database → Connect.

Verify connection in `backend/features/graph.py`:
```python
from neo4j import GraphDatabase
import os

driver = GraphDatabase.driver(
    os.getenv("NEO4J_URI"),
    auth=(os.getenv("NEO4J_USERNAME"), os.getenv("NEO4J_PASSWORD"))
)

def ping():
    with driver.session() as session:
        result = session.run("RETURN 1 AS n")
        return result.single()["n"] == 1
```

Once connected, re-run the generator so it writes graph edges to Neo4j.
Then re-run training so graph features have real values.

---

### FIX 10 — Deploy Celery worker on Render

Currently scoring runs synchronously in the webhook handler. This blocks the response.

In Render:
1. New + → Background Worker
2. Same repo, Root: backend
3. Start Command: `celery -A app.workers.tasks worker --loglevel=info`
4. Add all same environment variables

In `backend/app/api/webhooks.py`, change the webhook handler to enqueue instead of score:
```python
from app.workers.tasks import process_webhook_event

@router.post("/webhooks/razorpay")
async def receive_webhook(request: Request, db: Session = Depends(get_db)):
    # 1. Verify signature
    # 2. Deduplicate
    # 3. Persist raw envelope
    # 4. Return 200 IMMEDIATELY
    # 5. Enqueue Celery task
    process_webhook_event.delay(event_id, event_type, payload)
    return {"status": "received"}
```

---

## SECTION 3 — AFTER ALL FIXES, RE-RUN IN THIS ORDER

```bash
# 1. Generate fresh data with fixed labels and realistic prevalence
python backend/data/generator.py --seed 42
python backend/data/generator.py --seed 123
python backend/data/generator.py --seed 999

# 2. Train models on clean data
python backend/ml/train.py

# 3. Evaluate on frozen test set — run ONCE
python backend/ml/evaluate.py

# 4. Verify ring-level metrics appear in output
cat backend/ml/artifacts/evaluation_results.json | python -m json.tool | grep ring

# 5. Run all tests
cd backend && pytest tests/ -v

# 6. Run notebooks (in order, fresh kernel)
jupyter nbconvert --to notebook --execute notebooks/01_eda.ipynb
jupyter nbconvert --to notebook --execute notebooks/02_feature_correlation.ipynb
jupyter nbconvert --to notebook --execute notebooks/03_pr_curves.ipynb
jupyter nbconvert --to notebook --execute notebooks/04_shap_plots.ipynb

# 7. Commit everything
git add .
git commit -m "fix: correct labels, realistic prevalence, ring metrics, real features"
git push
```

---

## SECTION 4 — WHAT THE SUBMISSION FORM NEEDS

| Field | What to write |
|---|---|
| Full name | Your name |
| College | PW IOI under Medhavi Skills University |
| Graduation year | 2029 |
| In-person from September | Yes or No |
| 6 or 12 months | Your pick |
| Resume | Upload your resume |
| Track | AI Risk Manager |
| Project name | EncryptionGuard |
| What it solves | Detects coordinated refund abuse rings using graph signals, XGBoost scoring, and explainable AI |
| GitHub repo URL | Your public repo URL |
| 5-min pitch video | Unlisted YouTube link |
| What broke and how you got out | See below |

**What broke (write this — they read it first):**

"Render's free tier uses ephemeral storage, so SQLite data was wiped on every deploy — cases appeared in the morning and vanished by afternoon. We traced it to the ORM falling back to SQLite silently when the PostgreSQL connection string used the pooler format instead of the direct connection. Fixed by switching to the Supabase direct connection URL. Second issue: import paths used the backend. prefix locally but Render runs from inside the backend/ directory, causing ModuleNotFoundError on every deploy. Fixed by removing the prefix from all service imports."
