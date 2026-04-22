import os
import random
import asyncio
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)

# STATES
NAME, GROUP, SUBJECT, QUIZ = range(4)

# LOAD QUESTIONS
def load_questions(file):
    questions = []
    with open(file, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip()]

    for i in range(0, len(lines), 5):
        q = lines[i]
        correct = lines[i + 1]
        options = lines[i + 1:i + 5]

        random.shuffle(options)

        questions.append({
            "question": q,
            "options": options,
            "answer": correct
        })

    return questions


# SUBJECT FILES
SUBJECTS = {
    "Medicine": "Internal Medicine.txt",
    "Surgery": "Urology.txt",
    "Pediatrics": "Pediatrics.txt",
    "Pharma": "Clinical Pharmacology.txt",
    # add all your subjects here
}


# START
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Enter your name:")
    return NAME


async def get_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["name"] = update.message.text
    await update.message.reply_text("Enter your group:")
    return GROUP


async def get_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["group"] = update.message.text

    subjects_list = "\n".join(SUBJECTS.keys())
    await update.message.reply_text(f"Choose subject:\n{subjects_list}")

    return SUBJECT


async def select_subject(update: Update, context: ContextTypes.DEFAULT_TYPE):
    subject = update.message.text

    if subject not in SUBJECTS:
        await update.message.reply_text("Invalid subject, try again.")
        return SUBJECT

    file = SUBJECTS[subject]

    try:
        questions = load_questions(file)
    except:
        await update.message.reply_text("Error loading subject file.")
        return ConversationHandler.END

    random.shuffle(questions)

    context.user_data["questions"] = questions
    context.user_data["index"] = 0
    context.user_data["score"] = 0

    await update.message.reply_text(f"Starting {subject} quiz...")

    return await send_question(update, context)


# SEND QUESTION
async def send_question(update, context):
    idx = context.user_data["index"]
    questions = context.user_data["questions"]

    if idx >= len(questions):
        score = context.user_data["score"]
        total = len(questions)

        await update.message.reply_text(
            f"Quiz finished!\nScore: {score}/{total}"
        )
        return ConversationHandler.END

    q = questions[idx]

    text = f"Q{idx+1}. {q['question']}\n\n"
    for i, opt in enumerate(q["options"]):
        text += f"{i+1}. {opt}\n"

    await update.message.reply_text(text)

    # start timer
    context.user_data["answered"] = False
    asyncio.create_task(timeout(update, context))

    return QUIZ


# HANDLE ANSWER
async def handle_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("answered"):
        return QUIZ

    user_answer = update.message.text.strip()
    idx = context.user_data["index"]
    q = context.user_data["questions"][idx]

    correct = q["answer"]

    context.user_data["answered"] = True

    try:
        chosen = q["options"][int(user_answer) - 1]
    except:
        await update.message.reply_text("Invalid option. Use 1-4.")
        context.user_data["answered"] = False
        return QUIZ

    if chosen == correct:
        context.user_data["score"] += 1
        await update.message.reply_text("✅ Correct")
    else:
        await update.message.reply_text(f"❌ Wrong\nCorrect: {correct}")

    context.user_data["index"] += 1

    return await send_question(update, context)


# TIMEOUT
async def timeout(update, context):
    await asyncio.sleep(90)

    if context.user_data.get("answered"):
        return

    idx = context.user_data["index"]
    q = context.user_data["questions"][idx]

    context.user_data["answered"] = True

    await update.message.reply_text(
        f"⏰ Time up!\nCorrect: {q['answer']}"
    )

    context.user_data["index"] += 1

    await send_question(update, context)


# STOP
async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Quiz stopped.")
    return ConversationHandler.END


# MAIN
def main():
    print("Bot starting...")

    TOKEN = os.getenv("TOKEN")

    app = ApplicationBuilder().token(TOKEN).build()

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            GROUP: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_group)],
            SUBJECT: [MessageHandler(filters.TEXT & ~filters.COMMAND, select_subject)],
            QUIZ: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_answer)],
        },
        fallbacks=[CommandHandler("stop", stop)],
    )

    app.add_handler(conv)

    app.run_polling()


if __name__ == "__main__":
    main()