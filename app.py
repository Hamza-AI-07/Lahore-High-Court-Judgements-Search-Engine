import sys
import argparse
from cli import main as run_cli
from ui_app import app as flask_app

def main():
    parser = argparse.ArgumentParser(description="LHC Judgment Search System")
    parser.add_argument("--mode", choices=["cli", "ui"], default="cli", help="Run mode: cli or ui")
    parser.add_argument("--port", type=int, default=5000, help="Port for UI mode")
    args = parser.parse_args()

    if args.mode == "cli":
        run_cli()
    else:
        flask_app.run(debug=True, port=args.port)

if __name__ == "__main__":
    main()
