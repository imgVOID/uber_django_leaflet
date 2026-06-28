import os
from django.core.asgi import get_asgi_application

# 1. Спочатку встановлюємо змінні середовища
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'uber_django_leaflet.settings')

# 2. Отримуємо ASGI додаток
django_asgi_app = get_asgi_application()

# 3. Тепер імпортуємо речі, які потребують налаштованого Django
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from rides.routing import websocket_urlpatterns

# 4. Формуємо додаток
application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": AuthMiddlewareStack(
        URLRouter(websocket_urlpatterns)
    ),
})
