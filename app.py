from flask import Flask, render_template, request, redirect, url_for, session, flash
import re
import datetime
import secrets

app = Flask(__name__)
app.secret_key = secrets.token_hex(64)
@app.route('/')

def home():  # put application's code here

    # temporary session setter
    session["username"] = "admin"
    session["is_admin"] = True # change when testing different features
    return redirect(url_for('search'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    return render_template("login.html")

@app.route("/search", methods=['GET', 'POST'])
def search():

    test_data = {
        "WINSERVFYP.FYP.LOC": "1",
        "LINSERVFYP.FYP.LOC": "2",
        "FYPDC.FYP.LOC": "3"
    }

    if request.method == "GET":
        return render_template("search.html")
    query = request.form.get("query")
    r = re.compile(query, re.IGNORECASE)
    search_results = [(key, value) for key, value in test_data.items() if r.search(key)]
    if len(search_results) == 0:
        search_results = False

    return render_template("search.html", search_results=search_results)

@app.route('/logout')
def logout():
    session.clear()
    flash("You have been logged out")
    return redirect(url_for('login'))

@app.route('/computer/<computer_id>', methods=['GET', 'POST'])
def computer(computer_id):
    if "username" not in session:
        return redirect(url_for('login'))
    users = ["FYP\\Zythia",
        "FYP\\zythum",
        "FYP\\Zyzomys",
        "FYP\\Zyzzogeton",
        "FYP\\zyzzyva",
        "FYP\\zyzzyvas",
        "FYP\\ZZ",
        "FYP\\Zz",
        "FYP\\zZt",
        "FYP\\ZZZ"
    ]

    mock_details = {
        "computer_name": "WINSERVFYP.FYP.LOC",
        "os": "Windows Server 2019",
        "ip_address": "192.168.1.10",
        "users": users,
        "sessions": [
            {
                "username": "FYP\\demoadmin",
                "start_time": datetime.datetime.now(),
                "expiry_time": datetime.datetime.now() + datetime.timedelta(hours=4),
                "reason": "Software upgrade"
            }
        ]
    }
    # POST when a user is added to the admin list of the machine
    if request.method == "POST":
        if not session["is_admin"]:
            return redirect(url_for('computer', computer_id=computer_id))
        # Code to add user to computer here


    return render_template("computer_info.html", computer_details=mock_details)

@app.route("/session", methods=['GET', 'POST'])
def session_manager():
    if request.method == "POST":
        reason = request.json.get("reason")
        print("Reason: ", reason)
    return "<h1>GET</h1>"


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

