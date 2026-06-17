from dotenv import load_dotenv

load_dotenv()

from my_kitchen import create_app

app = create_app()

if __name__ == "__main__":
    app.run(host=app.config["HOST"], port=app.config["PORT"], debug=True)
