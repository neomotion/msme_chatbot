from auth import create_user, login_user, upgrade_plan
from chat import can_chat, record_chat, generate_openai_response
from db import users
import getpass

def main():
    print("🟢 MSME Chatbot — Login/Register")
    email = input("Email: ")
    user = users.find_one({"email": email})

    if not user:
        print("🔐 New user — please register.")
        password = getpass.getpass("Set password: ")
        success, msg = create_user(email, password)
        print(msg)
        if not success:
            return
        user = users.find_one({"email": email})
    else:
        password = getpass.getpass("Password: ")
        user = login_user(email, password)
        if not user:
            print("❌ Invalid credentials.")
            return

    print("✅ Logged in. Type 'exit' to quit.")

    while True:
        if not can_chat(user):
            print("\n🚫 You've used your message quota.")
            print("💳 Subscription Options:")
            print("1. Basic (100 messages/month)")
            print("2. Pro (unlimited)")
            print("3. Quit")
            choice = input("Choose a plan (1/2/3): ").strip()

            if choice == "1":
                upgrade_plan(user["_id"], "basic")
            elif choice == "2":
                upgrade_plan(user["_id"], "pro")
            else:
                print("👋 Exiting. Goodbye!")
                break
            user = users.find_one({"_id": user["_id"]})  # Refresh user data

        question = input("\nYou: ")
        if question.lower() in {"exit", "quit"}:
            print("👋 Goodbye!")
            break

        response, tokens_used = generate_openai_response(question)
        record_chat(user, question, response, tokens_used)
        print(f"Chatbot: {response}")

if __name__ == "__main__":
    main()