from flask import Flask
from testing import test
import os
print("FLASK_APP:", os.environ.get("FLASK_APP"))
print("FLASK_ENV:", os.environ.get("FLASK_ENV"))
app = Flask(__name__)


@app.route('/')
def hello_world():  # put application's code here
    return 'THIS IS A SECOND TEST'

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

