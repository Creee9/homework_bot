class NotSendMessage(Exception):
    """Сообщение не отправленою."""

    pass


class GetStatusException(Exception):
    """Ошибка неверного статуса ответа API."""

    pass


class ParseStatusException(Exception):
    """Ошибка неверного статуса домашней работы."""

    pass
