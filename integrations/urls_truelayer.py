from django.urls import path

from integrations.views_truelayer import (
    truelayer_callback,
    truelayer_connect,
    truelayer_sync,
)

urlpatterns = [
    path("truelayer/connect", truelayer_connect),
    path("truelayer/callback", truelayer_callback),
    path("truelayer/sync", truelayer_sync),
]
