# Безопасность и ограничения данных

Threat model: пользователь вводит произвольный текст; EPO/OpenAlex и внешние страницы содержат недоверенные данные; локальный inference может вернуть произвольный Markdown/URL/JSON; публичный reverse proxy потенциально доступен из Интернета. Приоритеты: изоляция пользователей, защита секретов, отсутствие прямого доступа к базам и безопасная цитата первоисточника.

- Аутентификация: серверная session cookie, Argon2id для локальных паролей или внешний OIDC; auth abstraction позволяет заменить механизм. У всех conversation/run/idea endpoints проверять ownership до cache/index. Межпользовательские тесты обязательны.
- Сеть: только Caddy публикует порт; PostgreSQL/Redis/Neo4j/Qdrant/inference в приватной Compose network. Для внешнего доступа HTTPS, HSTS после корректной настройки, CORS allowlist, CSRF token для cookie mutations, rate limit по user/IP.
- Ввод: лимиты размеров и типов, timeouts, quotas jobs, валидированные IDs и enums. Source URL строить из проверенных доменов/ID и позволять только `https`; запрет SSRF, redirects на внутренние адреса и произвольный fetch по URL от клиента.
- Вывод: Markdown рендерить с sanitization, без raw HTML/inline scripts; ссылки с `rel=noopener noreferrer`; evidence IDs сверять с snapshot. Источники и LLM output — данные, не инструкции для backend.
- Секреты: в env/secret store, не в Git/логи/URL; отдельный EPO OAuth token cache; ротация session secret и DB credentials, минимальные DB роли. `.gitignore` защищает только от случайной публикации: `git diff --cached` обязателен перед push.
- Данные: EPO OPS требует соблюдения [условий](https://www.epo.org/en/service-support/ordering/terms-and-conditions/ops-terms-and-conditions) и [fair use](https://www.epo.org/en/service-support/ordering/fair-use); не распространять скачанный корпус как raw dump. У OpenAlex хранить атрибуцию/source URL и перепроверить актуальные условия.
- Логи/backup: не логировать полные идеи, prompts, cookie, токены и raw responses. Шифрование диска/backup, доступ администратора, проверка восстановления и срока хранения. Удаление пользователя удаляет личные conversation/idea/run и очищает связанные caches, сохраняя разрешённые публичные документы.

Перед внешним demo провести проверку TLS, CORS/CSRF, session fixation, horizontal IDOR, prompt injection, SSRF, dependency versions, exposed ports и secret scanning. Запретить external demo при провале любой критичной проверки.
