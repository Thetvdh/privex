from flask import Flask, render_template, request, redirect, url_for, session, flash, abort
import re
import secrets
from hashlib import sha512
from DB import database
from ADScripts import ad_config
from Scanner.scanner import create_session
app = Flask(__name__)
app.secret_key = "48f5bc19c3f1addf59500533b70ac4dbe8c78fae7bd931bccaae163bb7ea8f11c25a60e57340feba21724be370fe5953130ec2758b78c4ef3b613ab53bf72cb8"


@app.route('/')
def home():  # put application's code here

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
        r = re.compile(re.escape(computer_name), re.IGNORECASE)

        search_results_final = [(key, value) for key, value in search_results.items() if r.search(key)]


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

    computer_details = database.web_get_computer_details(computer_id)
    if not computer_details:
        return abort(500)

    raw_sessions = database.get_sessions_by_computer_db(computer_details[1])

    admins = database.get_computer_admins(computer_details[1])
    admins = dict(admins)

    # Convert admin id to admin name for display
    new_admins = []
    for admin in admins.keys():
        admin_name = database.get_user_from_id(admin) if database.get_user_from_id(admin) else admin
        new_admins.append({"username": admin_name, "persistent": admins[admin]}) # Sets value to the persistent

    sessions = []

    for sesh in raw_sessions:
        username = database.get_user_from_id(sesh[1]) if database.get_user_from_id(sesh[1]) else sesh[1]
        sessions.append({
            "username": username,
            "start_time": sesh[2],
            "expiry_time": sesh[3],
            "reason": sesh[4]
        })


    details = {
        "computer_id": computer_id,
        "computer_name": computer_details[1],
        "os": computer_details[4],
        "ip_address": computer_details[3],
        "users": new_admins,
        "sessions": reversed(sessions)
    }

    # POST when a user is added to the admin list of the machine
    if request.method == "POST":
        if not session["is_admin"]:
            flash("You do not have the required permission to perform this action")
            return redirect(url_for('computer', computer_id=computer_id))
        print(request.form)
        if request.form.get("process") == "add":
            # Code to add user to computer here
            username = request.form.get("username")
            print(username)
            if not username[:3] == ad_config["DomainNetBIOSName"]:
                username = ad_config["DomainNetBIOSName"] + "\\" + username
            if database.add_user_to_admin(username, computer_details[1], ad_config["DomainNetBIOSName"]):
                flash(f"Successfully added {username} to the admin list")
                print(f"Successfully added {username} to the admin list")
                return redirect(url_for('computer', computer_id=computer_id))
            else:
                flash(f"Failed to add {username} to the admin list")
                print(f"Failed to add {username} to the admin list")

                return redirect(url_for('computer', computer_id=computer_id))
        elif request.form.get("process") == "remove":
            username = request.form.get("username")
            if database.remove_user_from_admin(username, computer_details[1]):
                flash(f"Successfully removed {username} from the admin list")
                print(f"Successfully removed {username} from the admin list")
                return redirect(url_for('computer', computer_id=computer_id))
            else:
                flash(f"Failed to remove {username} from the admin list")
                print(f"Failed to remove {username} from the admin list")
                return redirect(url_for('computer', computer_id=computer_id))
        else:
            flash("Invalid operation")
            return redirect(url_for('computer', computer_id=computer_id))

    return render_template("computer_info.html", computer_details=details)

@app.route("/session", methods=['POST'])
def session_manager():
    if request.method == "POST":
        reason = request.json.get("reason")
        computer_fqdn = request.json.get("computer_name")
        print("Reason: ", reason)
        web_session_name = session.get("username")  # Sessions username ie Jack
        ad_user_id = database.web_get_ad_name(web_session_name) # ad_user_id for user_name in current session
        ad_username = database.get_user_from_id(ad_user_id) # samAccountName for ad_user_id
        computer_id = database.get_computer_id(computer_fqdn)
        if not ad_username:
            print("Invalid username")
            return abort(403)

        print("[DEBUG]", web_session_name, ad_user_id, computer_id)
        if database.web_check_allowed_to_elevate(computer_id, ad_user_id):
            print("[DEBUG] Passed test")
            output = create_session(computer_fqdn, ad_username, reason)
            print("[DEBUG]", output)
            return "Successfully created session", 200
        else:
            print("Not allowed to elevate")
            return abort(403)
    return abort(500)


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

