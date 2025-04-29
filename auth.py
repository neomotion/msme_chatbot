from db import users
from datetime import datetime, timedelta
import bcrypt
from bson.binary import Binary

def create_user(email, password):
    if users.find_one({"email": email}):
        return False, "User already exists"
    password_hash = Binary(bcrypt.hashpw(password.encode(), bcrypt.gensalt()))
    users.insert_one({
        "email": email,
        "password_hash": password_hash,
        "plan": "free",
        "used_messages": 0,
        "subscription_expiry": None,
        "created_at": datetime.utcnow()
    })
    return True, "User created successfully."


import bson


from bson.binary import Binary

def login_user(email, password):
    user = users.find_one({"email": email})
    if not user:
        return None

    password_hash = user.get("password_hash")

    # Convert BSON Binary to bytes if necessary
    if isinstance(password_hash, Binary):
        password_hash = bytes(password_hash)

    if not bcrypt.checkpw(password.encode(), password_hash):
        return None

    return user



def upgrade_plan(user_id, plan):
    expiry = datetime.utcnow() + timedelta(days=30)
    users.update_one(
        {"_id": user_id},
        {"$set": {"plan": plan, "subscription_expiry": expiry, "used_messages": 0}}
    )
