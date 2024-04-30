from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import os
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import pickle
import logging

# Налаштування логування
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()

# Словник для зберігання активних списків завдань користувачів
user_task_lists = {}

# Створення завдання в Google Tasks
def create_task(service, tasklist_id, task_title):
    task = {'title': task_title}
    result = service.tasks().insert(tasklist=tasklist_id, body=task).execute()
    return result.get('title')

# Отримання списку всіх завдань у списку
def list_tasks(service, tasklist_id):
    results = service.tasks().list(tasklist=tasklist_id).execute()
    tasks = results.get('items', [])
    if not tasks:
        return "У даному списку завдань немає завдань."
    else:
        return "\n".join([f"{task['title']} (ID: {task['id']})" for task in tasks])

# Видалення завдання
def delete_task(service, tasklist_id, task_id):
    service.tasks().delete(tasklist=tasklist_id, task=task_id).execute()
    return "Завдання видалено."

# Отримання та оновлення облікових даних Google
def get_credentials():
    creds = None
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', scopes=['https://www.googleapis.com/auth/tasks'])
            creds = flow.run_local_server(port=8080)
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)
    return creds

# Команда start
# Команда start з оновленим текстом вітання
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_message = (
        "Привіт! Я бот для управління завданнями в Google Tasks. Ось що я можу робити:\n"
        "/setlist <ID списку> - Встановити активний список завдань.\n"
        "/newtask <назва завдання> - Створити нове завдання в активному списку.\n"
        "/listtasks - Показати всі завдання в активному списку.\n"
        "/deletetask <ID завдання> - Видалити завдання з активного списку.\n"
        "/createtasklist <назва списку> - Створити новий список завдань.\n"
        "/listtasklists - Показати всі списки завдань.\n"
        "/deletetasklist <ID списку> - Видалити список завдань.\n"
        "Спочатку встановіть активний список завдань за допомогою команди /setlist!"
    )
    await update.message.reply_text(welcome_message)


# Встановлення активного списку завдань
async def set_task_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        tasklist_id = ' '.join(context.args)
        if not tasklist_id:
            await update.message.reply_text('Будь ласка, вкажіть ID списку завдань після команди.')
            return
        user_task_lists[update.effective_user.id] = tasklist_id
        await update.message.reply_text(f'Активний список завдань встановлено: {tasklist_id}')
    except Exception as e:
        logger.error(f"Помилка: {e}")
        await update.message.reply_text('Виникла помилка, будь ласка, спробуйте ще раз.')


# Команда для створення нового завдання
async def new_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in user_task_lists:
        await update.message.reply_text('Спочатку встановіть активний список завдань за допомогою /setlist.')
        return

    task_title = ' '.join(context.args)
    if not task_title:
        await update.message.reply_text('Будь ласка, вкажіть назву завдання після команди.')
        return

    tasklist_id = user_task_lists[update.effective_user.id]
    creds = get_credentials()
    service = build('tasks', 'v1', credentials=creds)
    result = create_task(service, tasklist_id, task_title)
    await update.message.reply_text(f'Завдання "{result}" створено в списку з ID {tasklist_id}.')

# Команда для перегляду завдань в активному списку
async def list_tasks_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in user_task_lists:
        await update.message.reply_text('Спочатку встановіть активний список завдань за допомогою /setlist.')
        return

    tasklist_id = user_task_lists[update.effective_user.id]
    creds = get_credentials()
    service = build('tasks', 'v1', credentials=creds)
    result = list_tasks(service, tasklist_id)
    await update.message.reply_text(f"Завдання в списку {tasklist_id}:\n{result}")

# Команда для видалення завдання з активного списку
async def delete_task_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in user_task_lists:
        await update.message.reply_text('Спочатку встановіть активний список завдань за допомогою /setlist.')
        return

    if len(context.args) < 1:
        await update.message.reply_text('Використання: /deletetask <ID завдання>')
        return

    task_id = context.args[0]
    tasklist_id = user_task_lists[update.effective_user.id]
    creds = get_credentials()
    service = build('tasks', 'v1', credentials=creds)
    result = delete_task(service, tasklist_id, task_id)
    await update.message.reply_text(result)
# Створення нового списку завдань
def create_task_list(service, title):
    tasklist = {'title': title}
    result = service.tasklists().insert(body=tasklist).execute()
    return f"Список завдань '{result['title']}' створено з ID {result['id']}."

# Отримання усіх доступних списків завдань
def get_task_lists(service):
    results = service.tasklists().list().execute()
    tasklists = results.get('items', [])
    if not tasklists:
        return "Немає доступних списків завдань."
    else:
        return "\n".join([f"{tasklist['title']} (ID: {tasklist['id']})" for tasklist in tasklists])

# Видалення списку завдань
def delete_task_list(service, tasklist_id):
    service.tasklists().delete(tasklist=tasklist_id).execute()
    return f"Список завдань з ID {tasklist_id} видалено."
# Команда для створення нового списку завдань
async def create_task_list_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    title = ' '.join(context.args)
    if not title:
        await update.message.reply_text('Вкажіть назву для нового списку завдань після команди.')
        return

    creds = get_credentials()
    service = build('tasks', 'v1', credentials=creds)
    result = create_task_list(service, title)
    await update.message.reply_text(result)

# Команда для перегляду усіх списків завдань
async def list_task_lists_command(update: Update, context:

 ContextTypes.DEFAULT_TYPE):
    creds = get_credentials()
    service = build('tasks', 'v1', credentials=creds)
    result = get_task_lists(service)
    await update.message.reply_text(f"Доступні списки завдань:\n{result}")

# Команда для видалення списку завдань
async def delete_task_list_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tasklist_id = ' '.join(context.args)
    if not tasklist_id:
        await update.message.reply_text('Вкажіть ID списку завдань для видалення після команди.')
        return

    creds = get_credentials()
    service = build('tasks', 'v1', credentials=creds)
    result = delete_task_list(service, tasklist_id)
    await update.message.reply_text(result)

def main():
    application = Application.builder().token('6986971673:AAGrmYs2z9H-qPabgD_-3rhk_qMa3PFfWGc').build()

    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('setlist', set_task_list))
    application.add_handler(CommandHandler('newtask', new_task))
    application.add_handler(CommandHandler('listtasks', list_tasks_command))
    application.add_handler(CommandHandler('deletetask', delete_task_command))
    application.add_handler(CommandHandler('createtasklist', create_task_list_command))
    application.add_handler(CommandHandler('listtasklists', list_task_lists_command))
    application.add_handler(CommandHandler('deletetasklist', delete_task_list_command))

    application.run_polling()

if __name__ == '__main__':
    main()