import logging
import os
import sys
import requests
import time
import telegram

# from telegram.ext import Updater
from dotenv import load_dotenv
from logging import StreamHandler
from exceptions import GetStatusException
load_dotenv()


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

ONE_MONTH_TIME = 2629743
RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

logging.basicConfig(
    format='%(asctime)s, %(levelname)s, %(message)s, %(name)s',
    level=logging.DEBUG,
    filename='main.log',
    filemode='w',
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = StreamHandler(stream=sys.stdout)
logger.addHandler(handler)
formatter = logging.Formatter(
    '%(asctime)s, %(levelname)s, %(message)s, %(name)s'
)
handler.setFormatter(formatter)

HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def check_tokens():
    """Проверка доступность переменных окружения."""
    interable = {
        PRACTICUM_TOKEN: 'PRACTICUM_TOKEN',
        TELEGRAM_TOKEN: 'TELEGRAM_TOKEN',
        TELEGRAM_CHAT_ID: 'TELEGRAM_CHAT_ID',
    }
    if not all(interable):
        for k, v in interable.items():
            if not k:
                logger.critical(
                    msg=(f'Required environment variable is missing: {v}!'
                         ' The program is forcibly stopped.')
                )
        sys.exit('Telegram bot is not running! '
                 'There are no mandatory environment variables!')


def send_message(bot, message):
    """Отправляет сообщение в Telegram чат."""
    chat_id = TELEGRAM_CHAT_ID
    try:
        bot.send_message(chat_id, message)
        logger.debug('Message was send successfuly!')
    except telegram.TelegramError as error:
        logger.error(f'Сообщение не отправлено: {error}')


def get_api_answer(timestamp):
    """Делает запрос к единственному эндпоинту API-сервиса."""
    headers = HEADERS
    payload = {'from_date': timestamp}
    try:
        response = requests.get(ENDPOINT, headers=headers, params=payload)
    except requests.exceptions.RequestException as error:
        logger.error(error, exc_info=True)
        raise GetStatusException(f'Ошибка при запросе к основному API:{error}')

    if response.status_code != 200:
        logger.error('Статус ответа не 200')
        raise GetStatusException(
            f'Ошибка, код ответа: {requests.status_codes}'
        )

    return response.json()


def check_response(response):
    """Проверяет ответ API на соответствие документации."""
    if not isinstance(response, dict):
        logger.error('Ответ API не является словарем')
        raise TypeError('Ответ API не является словарем')
    if 'homeworks' not in response:
        logger.error('Отсустсвует ключ "homework_name" в ответ API')
        raise KeyError('Отсустсвует ключ "homework_name" в ответ API')
    response = response.get('homeworks')
    # response = response['homeworks']

    if not isinstance(response, list):
        logger.error('Ответ API не является списком')
        raise TypeError('Ответ API не является списком')

    return response


def parse_status(homework):
    """Извлекает из информации о конкретной домашней работе."""
    if 'homework_name' not in homework:
        logger.error('Отсутствует ключ "homework_name" в ответе API')
        raise KeyError('Отсутствует ключ "homework_name" в ответе API')
    if 'status' not in homework:
        logger.error('Отсутствует ключ "status" в ответе API')
        raise KeyError('Отсутствует ключ "status" в ответе API')
    try:
        homework_name = homework.get('homework_name')
        status = homework.get('status')
        if homework_name is None or status is None:
            logger.error('Oшибка при запросе данных')
            raise TypeError(
                f'Ошибка получения данных homework_name: '
                f'{homework_name} и status: {status}'
            )
        verdict = HOMEWORK_VERDICTS[status]
    except Exception as error:
        logger.error(f'Передан неизвестный статус домашней работы: {error}')
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'

    # ЧИСТО ДЛЯ СЕБЯ! Мои неудачные попытки пройти Pytest)

    # for status, verdict in HOMEWORK_VERDICTS.items():
    #     homework_name = homework.get('homework_name')
    #     if status == homework.get('status'):
    #          return 'Изменился статус проверки '\
    #                f'работы "{homework_name}". {verdict}'
    #     else:
    #        raise TypeError('Ошибка извлечения данных')

    # homework_name = homework.get('homework_name')
    # status = homework.get('status')
    # verdict = HOMEWORK_VERDICTS[status]
    # if status in HOMEWORK_VERDICTS.keys():
    #     return (f'Изменился статус проверки работы '
    #             f'"{homework_name}". {verdict}')
    # else:
    #     raise ValueError('Вы выйграли ааааафтамабиль!')

    # if status in HOMEWORK_VERDICTS:
    #    return 'Изменился статус проверки ' \
    #           f'работы "{homework_name}". {verdict}'
    # else:
    #    message = f'Передан неизвестный статус домашней работы: {status}'
    #    logger.error(message)
    #    raise ParseStatusException(message)


def main():
    """Основная логика работы бота."""
    check_tokens()
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())  # - ONE_MONTH_TIME
    current_report = {}
    prev_report = {}
    while True:
        try:
            response = get_api_answer(timestamp)
            homework = check_response(response)[0]
            if homework:
                message = parse_status(homework)
                current_report[
                    response.get('homework_name')] = response.get('status')
                if current_report != prev_report:
                    send_message(bot, message)
                    prev_report = current_report.copy()
                    current_report[
                        response.get('homework_name')] = response.get('status')
                else:
                    logger.debug('CТатус не изменился')
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(message)
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
