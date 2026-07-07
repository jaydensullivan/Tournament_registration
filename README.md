# SHOT CS:GO Cup — Telegram-бот регистрации и сетки

Бот принимает индивидуальные заявки от подписчиков, хранит их в SQLite,
позволяет админу вручную собрать команды из заявок и сгенерировать
турнирную сетку на выбывание прямо в чате — с инлайн-кнопками для
выбора победителя каждого матча.

## Что умеет

**Для игроков:**
- `/start` — регистрация: ник + Steam-профиль
- `/myinfo` — посмотреть свою заявку

**Для админов** (Telegram ID из `ADMIN_IDS` в `.env`):
- `/players` — список всех, кто подал заявку (с их tg_id)
- `/add_team НазваниеКоманды id1 id2 id3 id4 id5` — собрать команду из заявок
- `/teams` — список сформированных команд
- `/generate_bracket` — сгенерировать сетку на выбывание (поддерживает
  нечётное/непарное число команд через автопроходы)
- `/bracket` — показать текущее состояние сетки
- Победитель матча выбирается кнопкой под сообщением — бот сам
  продвигает команду в следующий раунд и присылает следующий матч

## Установка (локально, для проверки)

```bash
cd shot_tournament_bot
python3 -m venv venv
source venv/bin/activate        # на Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

Откройте `.env` и впишите:
- `BOT_TOKEN` — токен, который вам выдал @BotFather
- `ADMIN_IDS` — ваш Telegram ID (и других организаторов через запятую).
  Узнать свой ID можно у бота **@userinfobot** — просто напишите ему `/start`.

Запуск:
```bash
python bot.py
```

Если всё настроено верно, бот начнёт отвечать в Telegram. База данных
(`tournament.db`) создастся автоматически рядом с `bot.py`.

## Регистрация по ссылке

Просто дайте подписчикам ссылку вида `https://t.me/ваш_бот_username` —
переход по ней и нажатие Start запускает регистрацию. Отдельная
диплинк-логика не нужна, `/start` уже делает всё нужное.

## Деплой на постоянку

Бот работает через long polling — значит, скрипт должен работать
непрерывно на каком-то сервере. Варианты:

### Вариант A — свой VPS (Ubuntu), самый предсказуемый
```bash
sudo apt update && sudo apt install python3-venv -y
# скопируйте папку shot_tournament_bot на сервер, затем:
cd shot_tournament_bot
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Создайте systemd-юнит, чтобы бот поднимался автоматически и
перезапускался при падении — `/etc/systemd/system/shot-bot.service`:
```ini
[Unit]
Description=SHOT CS:GO Cup Telegram Bot
After=network.target

[Service]
WorkingDirectory=/root/shot_tournament_bot
ExecStart=/root/shot_tournament_bot/venv/bin/python bot.py
Restart=always
EnvironmentFile=/root/shot_tournament_bot/.env

[Install]
WantedBy=multi-user.target
```

Затем:
```bash
sudo systemctl daemon-reload
sudo systemctl enable shot-bot
sudo systemctl start shot-bot
sudo journalctl -u shot-bot -f   # посмотреть логи
```

Подойдёт любой недорогой VPS (1 CPU / 512 МБ RAM с запасом хватает
для такого бота).

### Вариант B — облачные платформы с фоновым воркером
Railway, Render, Fly.io и подобные сервисы поддерживают запуск
Python-скрипта как «background worker» без своего сервера — заливаете
репозиторий, указываете команду запуска `python bot.py` и переменные
окружения `BOT_TOKEN` / `ADMIN_IDS` в настройках проекта. Уточните
актуальные шаги и условия на сайте выбранной платформы — они периодически
меняют интерфейс и тарифы.

## Ограничения текущей версии (MVP)

- Команды собираются вручную командой `/add_team` — нет автосборки
  случайных команд из заявок (можно добавить отдельной командой, если
  нужно).
- Только формат single elimination (на выбывание). Групповой этап или
  double elimination не реализованы.
- Один турнир одновременно (`/generate_bracket` очищает предыдущую сетку).
- Считаем, что редактируете `.env` вручную; для команды организаторов
  из нескольких человек это ок, для более гибкого управления ролями
  потребуется расширение.

Если что-то из этого нужно — дайте знать, дополню.
