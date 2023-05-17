"""
Define the urls for the API app. It decides which views map to which endpoints.
"""
from django.urls import path
from .views import (
    RoomView,
    CreateRoomView,
    GetRoomView,
    JoinRoom,
    UserInRoom,
    LeaveRoom,
    UpdateRoom,
)

urlpatterns = [
    path("room", RoomView.as_view()),
    path("create-room", CreateRoomView.as_view()),
    path("get-room", GetRoomView.as_view()),
    path("join-room", JoinRoom.as_view()),
    path("user-in-room", UserInRoom.as_view()),
    path("leave-room", LeaveRoom.as_view()),
    path("update-room", UpdateRoom.as_view()),
]
