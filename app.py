from flask import Flask, render_template, request, redirect, url_for, session, flash

import datetime

app = Flask(__name__)

@app.route('/')

def home():  # put application's code here
    return redirect(url_for('search'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    return render_template("login.html")

@app.route("/search", methods=['GET', 'POST'])
def search():
    return render_template("search.html")

@app.route('/logout')
def logout():
    session.clear()
    flash("You have been logged out")
    return redirect(url_for('login'))

@app.route('/computer/<computer_id>', methods=['GET', 'POST'])
def computer(computer_id):
    mock_details = {
        "computer_name": "WINSERVFYP.FYP.LOC",
        "os": "Windows Server 2019",
        "users": [
            "FYP\\demoadmin", "FYP\\basic"
        ],
        "sessions": [
            {
                "username": "FYP\\demoadmin",
                "start_time": datetime.datetime.now(),
                "reason": "Software upgrade"
            }
        ]
    }
    return render_template("computer_info.html", computer_details=mock_details)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

