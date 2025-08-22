from prefect import flow, task

@task
def ingest(): print("INGEST (Prefect): new data")
@task
def features(): print("FEATURES (Prefect): build features")
@task
def train(): print("TRAIN (Prefect): training job")
@task
def backtest(): print("BACKTEST (Prefect): evaluate")

@flow(name="daily_ingest_features")
def daily_ingest_features():
    ingest(); features()

@flow(name="train_backtest_nightly")
def train_backtest_nightly():
    train(); backtest()

if __name__ == "__main__":
    daily_ingest_features()
    train_backtest_nightly()
