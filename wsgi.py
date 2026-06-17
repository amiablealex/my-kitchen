from dotenv import load_dotenv

load_dotenv()

from my_kitchen import create_app

app = create_app()
