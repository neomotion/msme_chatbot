from flask import Flask, render_template, request, redirect, session, url_for
from datetime import timedelta, datetime
from bson.objectid import ObjectId

# Import helper functions from modules
from auth import create_user, login_user, upgrade_plan
from chat import generate_openai_response, can_chat, record_chat
from db import users, db, chat_history

app = Flask(__name__)
app.secret_key = "supersecretkey"  # Use .env in production

# Subscription plans
PLANS = {
    "free": {"name": "Free", "message_limit": 5, "price": "0/month"},
    "basic": {"name": "Basic", "message_limit": 100, "price": "100/month"},
    "pro": {"name": "Pro", "message_limit": "Unlimited", "price": "300/month"}
}


@app.route("/")
def index():
    if "user_id" in session:
        return redirect("/chat")  # If the user is logged in, take them to the chat page
    return render_template("landing.html")  # Otherwise, render the landing page


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        # Use the login_user function from auth.py
        user = login_user(email, password)
        if user:
            session["user_id"] = str(user["_id"])
            return redirect("/chat")

        return render_template("login.html", error="Invalid credentials")

    return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        selected_plan = request.form["plan"]

        # Use the create_user function from auth.py
        success, message = create_user(email, password)
        if not success:
            return render_template("register.html", error=message)

        # Update the user's plan after creation
        user = users.find_one({"email": email})
        if selected_plan != "free":
            upgrade_plan(user["_id"], selected_plan)

        return redirect("/login")

    return render_template("register.html")


@app.route("/chat", methods=["GET", "POST"])
def chat():
    if "user_id" not in session:
        return redirect("/login")

    # Get user from session
    user = users.find_one({"_id": ObjectId(session["user_id"])})

    # Check if the user can chat based on their plan and usage
    if not can_chat(user):
        return redirect("/upgrade")

    # Retrieve the chat history for the current user
    chat_history_data = []
    chat_records = chat_history.find({"user_id": user["_id"]}).sort("timestamp", 1)

    for record in chat_records:
        chat_history_data.append({
            "question": record["question"],
            "answer": record["answer"],
            "timestamp": record["timestamp"]
        })

    # If POST request (new message)
    if request.method == "POST":
        question = request.form["message"]
        response, tokens_used = generate_openai_response(question,user)  # Get response and token usage

        # Record chat using helper function
        record_chat(user, question, response, tokens_used)

        # Reload chat history after new message
        chat_records = chat_history.find({"user_id": user["_id"]}).sort("timestamp", 1)
        chat_history_data = [
            {"question": record["question"], "answer": record["answer"], "timestamp": record["timestamp"]}
            for record in chat_records]

    return render_template("chat.html", chat_history=chat_history_data, user=user)


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


@app.route("/upgrade", methods=["GET", "POST"])
def upgrade():
    if "user_id" not in session:
        return redirect("/login")

    user = users.find_one({"_id": ObjectId(session["user_id"])})

    if request.method == "POST":
        selected_plan = request.form.get("plan")
        if selected_plan in PLANS:
            # Use the upgrade_plan function from auth.py
            upgrade_plan(user["_id"], selected_plan)
            return redirect("/chat")

    return render_template("upgrade.html", user=user, plans=PLANS)


if __name__ == "__main__":
    app.run(debug=True)