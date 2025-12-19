from dotenv import load_dotenv
from flask_app import create_app

# Load environment variables from .env file
load_dotenv()

app = create_app()

if __name__ == "__main__":
    app.run(debug=True)