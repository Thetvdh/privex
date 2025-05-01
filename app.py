from flask import Flask, render_template, request, redirect, url_for, session, flash, abort
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
    if request.method == "GET":
        return render_template("login.html")

    username = request.form.get('username')
    password = request.form.get('password')
    # Code to get valid users here, temporary values for now
    if username == "admin" and password == "dud_password":
        session["is_admin"] = True
        session["username"] = username
        return redirect(url_for('search'))
    flash("Invalid username or password")
    return render_template("login.html")

@app.route("/search", methods=['GET', 'POST'])
def search():

    if "username" not in session:
        return redirect(url_for('login'))
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

@app.route("/admin", methods=['GET', 'POST'])
def admin():
    admins = ["demoadmin"]
    if "username" not in session:
        return redirect(url_for('login'))
    if not session["is_admin"]:
        return redirect(url_for('search'))

    # Code to add users to the website here
    if request.method == "POST":
        username = request.form.get('username')
        process = request.form.get('process')

        if not username or not process:
            flash("Failed to perform action")
            return redirect(url_for('admin'))

        if process == "add":

            # Code for adding user to the platform here

            flash(f"Successfully added {username} to users")
            return redirect(url_for("admin"))
        elif process == "remove":
            # Check to ensure the currently logged in admin cannot be removed
            if session["username"] != username:
                flash(f"Successfully removed {username} from users")
                return redirect(url_for("admin"))
            flash(f"Unable to remove {username} as that is the currently logged in user")
            return redirect(url_for("admin"))
        else:
            flash("Failed to perform action")
            return redirect(url_for("admin"))

    return render_template("admin.html", admins=admins)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

