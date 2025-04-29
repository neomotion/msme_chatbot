import openai
from instructor.cli.usage import api_key

from db import users, chat_history
from datetime import datetime

client = openai.OpenAI(api_key=api_key)  # or use env var

SYSTEM_PROMPT = (
    "You are an expert chatbot designed to answer only questions about MSME (Micro, Small and Medium Enterprises) schemes in India. "
    "If the question is not about MSME schemes, politely decline to answer. Also make the answers very accurate and highly specific to the question"
)

def can_chat(user):
    """Check if the user can chat based on their plan, message count, and subscription expiration."""

    # Handle expired plans for basic and pro users
    if user["plan"] in ["basic", "pro"]:
        if user.get("subscription_expiry") and datetime.utcnow() > user["subscription_expiry"]:
            # If the subscription has expired, revert to free plan and reset message count
            users.update_one({"_id": user["_id"]}, {"$set": {"plan": "free", "used_messages": 0}})
            user["plan"] = "free"  # Refresh user data with free plan
            user["used_messages"] = 0  # Reset the used messages count

    # Handle the different plan logic
    if user["plan"] == "pro":
        # Pro users can always chat, as they have unlimited messages
        return True

    if user["plan"] == "basic":
        # Basic users can chat as long as they haven't exceeded 100 messages
        return user["used_messages"] < 100

    # Free plan users: Can chat only if they have messages remaining
    return user["used_messages"] < 5


def generate_openai_response(question, user):
    normalized_question = question.lower().strip()

    # Check if question already exists in cache (exact match)
    existing_chat = chat_history.find_one({
        "user_id": user["_id"],
        "normalized_question": normalized_question
    })

    if existing_chat:
        # Count it as a used interaction
        users.update_one({"_id": user["_id"]}, {"$inc": {"used_messages": 1}})
        return existing_chat["answer"], 0  # Return cached answer, zero tokens

    # Not found — generate a new response
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": question}
        ],
        temperature=0.7
    )

    answer = response.choices[0].message.content.strip()
    tokens_used = response.usage.total_tokens

    # Store chat in DB
    record_chat(user, question, answer, tokens_used)

    return answer, tokens_used


def record_chat(user, question, answer, tokens_used, used_context=False, metadata={}):
    chat_history.insert_one({
        "user_id": user["_id"],
        "question": question,
        "normalized_question": question.lower().strip(),
        "answer": answer,
        "timestamp": datetime.utcnow(),
        "used_context": used_context,
        "metadata": {
            **metadata,
            "tokens_used": tokens_used
        }
    })
    users.update_one({"_id": user["_id"]}, {"$inc": {"used_messages": 1}})