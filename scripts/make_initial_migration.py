import os
import sys
from dotenv import load_dotenv

# Ensure the project root is on sys.path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

load_dotenv()

from flask_migrate import migrate, upgrade
from app import create_app

def main() -> None:
    app, _ = create_app()
    with app.app_context():
        migrate(message="initial schema")
        upgrade()

if __name__ == "__main__":
    main()


