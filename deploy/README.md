Как я обновляю бота на сервере

1. Купи VPS (Ubuntu 22.04), получи IP.

2. В панели хостинга (или по паролю root) добавь этот ключ в `/root/.ssh/authorized_keys`:

```
ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIJJlKz0iXHGK5rHvKsG0Y0MOaDezl5ZCwLEDpx8ZSfyp katin-bot-cursor
```

Он же лежит в `deploy/katin_bot.pub`.

3. Впиши IP в `deploy/server.env`:

```
HOST=1.2.3.4
USER=root
REMOTE_DIR=/opt/katin-bot
```

и то же число в `C:\Users\Алексей\.ssh\config` вместо `REPLACE_WITH_SERVER_IP` у Host katin.

4. Напиши в чат: IP готов — и я сам залью код, поставлю systemd и буду обновлять через SSH.

После этого правки из Cursor уезжают командой `deploy\update.ps1` без ручной заливки.
