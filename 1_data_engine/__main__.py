"""
Package entry point — re-exports main() from .main so that

    python -m 1_data_engine generate --profile small --new-pipeline

works exactly as the README documents. The actual CLI lives in
`1_data_engine.main`.
"""
from .main import main

if __name__ == "__main__":
    main()
