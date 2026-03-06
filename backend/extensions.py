from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from flask_compress import Compress


db = SQLAlchemy()
cors = CORS()
compress = Compress()
