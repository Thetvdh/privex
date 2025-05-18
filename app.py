from flask import Flask, render_template, request, redirect, url_for, session, flash
import re
import datetime
import secrets
from hashlib import sha512
from DB import database
app = Flask(__name__)
# app.secret_key = secrets.token_hex(64)
app.secret_key = "TEMP"
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

    db_user = database.get_web_user(username)
    if not db_user:
        flash("Invalid username or password")
        return redirect(url_for('login'))

    salt = db_user[2]
    salted_password = password + salt
    hashed_password = sha512(salted_password.encode()).hexdigest()
    if hashed_password == db_user[1]:
        session['username'] = username
        session['is_admin'] = db_user[4]
        return redirect(url_for('search'))
    else:
        flash("Invalid username or password")
        return redirect(url_for('login'))


@app.route("/search", methods=['GET', 'POST'])
def search():
    search_results_final = []
    if "username" not in session:
        return redirect(url_for('login'))

    if request.method == "POST":
        computer_name = request.form.get("query")

        search_results = database.web_get_all_database_computers()

        search_results = dict(search_results)
        print(" FROM DB ", search_results)
        r = re.compile(computer_name, re.IGNORECASE)

        search_results_final = [(key, value) for key, value in search_results.items() if r.search(key)]
        print(" AFTER RE ", search_results_final)


    return render_template("search.html", search_results=search_results_final)

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
        return f"<h1>test</h1>"
    return "<h1>GET</h1>", 200

@app.route("/admin", methods=['GET', 'POST'])
def admin():
    if "username" not in session:
        return redirect(url_for('login'))
    if not session["is_admin"]:
        return redirect(url_for('search'))

    # Code to add users to the website here
    if request.method == "POST":
        username = request.form.get('username')
        ad_username = request.form.get('ad_username')
        process = request.form.get('process')

        if not username or not process:
            flash("Failed to perform action")
            return redirect(url_for('admin'))

        if process == "add":

            # Code for adding user to the platform here
            password = secrets.token_hex(8)
            result = database.add_web_user(username, password, ad_username)
            if result:
                flash(f"Successfully added {username} to users. Password set to {password}. Ask the user to update on first login!")
                return redirect(url_for("admin"))
            else:
                flash(f"Failed to add {username} to users. Potentially the username already exists or the AD user does not exist")
                return redirect(url_for('admin'))
        elif process == "remove":
            # Check to ensure the currently logged in admin cannot be removed
            if session["username"] != username:
                result = database.remove_web_user(username)
                if result:
                    flash(f"Successfully removed {username} from users")
                    return redirect(url_for("admin"))
            flash(f"Unable to remove {username} as that is the currently logged in user")
            return redirect(url_for("admin"))

        elif process == "make_admin":
            username = request.form.get('username')
            database.make_web_admin(username)

        else:
            flash("Failed to perform action")
            return redirect(url_for("admin"))



    raw_admins = database.get_all_web_users()
    admins = [admin[1] for admin in raw_admins]
    return render_template("admin.html", admins=admins)

@app.route("/changepassword", methods=['GET', 'POST'])
def changepassword():
    if request.method == "GET":
        return render_template("change_password.html")
    user = session["username"]

    password = request.form.get("password")

    # Code to update password in database here
    if database.reset_web_password(user, password):
        flash(f"Password successfully changed for user {user}")
        session.clear()
        return redirect(url_for("login"))
    flash(f"Failed to change password for user {user}")
    return redirect(url_for("changepassword"))




if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

