"""
setup_and_run.py
Pipeline bootstrap: optional dlt+dbt → Neo4j graph load → ChromaDB → ML train.

Env:
  MOC_PIPELINE=legacy   — old seed_neo4j only (default if Snowflake not configured)
  MOC_PIPELINE=full     — dlt → dbt → graph_loader → chroma → train
"""
import os
import subprocess
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent


def step(msg):
    print(f"\n{'='*60}\n{msg}\n{'='*60}")


def _run(cmd, cwd=None):
    print(f"$ {' '.join(cmd)}")
    subprocess.check_call(cmd, cwd=cwd or str(_ROOT))


mode = os.getenv("MOC_PIPELINE", "legacy").lower()

if mode == "full":
    step("0/5  Snowflake bootstrap (warehouse + schemas)...")
    try:
        _run([sys.executable, str(_ROOT / "scripts" / "bootstrap_snowflake.py")])
    except Exception as e:
        print(f"WARN bootstrap: {e}")

    step("1/5  dlt bronze load...")
    try:
        _run([sys.executable, "-m", "ingest.pipeline"])
    except Exception as e:
        print(f"ERROR dlt: {e}")
        sys.exit(1)

    step("2/5  dbt build (SILVER + GOLD)...")
    try:
        _run(["dbt", "build", "--profiles-dir", "."], cwd=str(_ROOT / "dbt_moc"))
    except Exception as e:
        print(f"ERROR dbt: {e}")
        sys.exit(1)

    step("3/5  Loading Neo4j from GOLD graph marts...")
    try:
        from loaders.graph_loader import load as graph_load
        graph_load(clear=True)
    except Exception as e:
        print(f"ERROR graph_loader: {e}")
        sys.exit(1)
else:
    step("1/3  Seeding Neo4j knowledge graph...")
    try:
        from core.seed_neo4j import seed
        seed(clear=True)
        print("Neo4j seeded successfully.")
    except Exception as e:
        print(f"ERROR seeding Neo4j: {e}")
        print("Make sure Neo4j is running and credentials are in .env")
        sys.exit(1)

step("Seeding ChromaDB vector store...")
try:
    from seed_vector_store import seed as seed_vs
    seed_vs()
    print("ChromaDB seeded successfully.")
except Exception as e:
    print(f"ERROR seeding ChromaDB: {e}")
    sys.exit(1)

step("Training ML prediction models...")
try:
    from train_predictor import train
    train()
    print("ML models trained and saved.")
except Exception as e:
    print(f"ERROR training models: {e}")
    sys.exit(1)

print("\n" + "="*60)
print("Setup complete! Run the app with:")
print("  streamlit run app.py")
print("  or: uvicorn api.main:app --reload")
print("="*60)
