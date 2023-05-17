"""
Define the urls for the API app. It decides which views map to which endpoints.
"""
from django.urls import path
from .views import (
    RoomView,
    CreateRoomView,
    GetRoomView,
    JoinRoomView,
    UserInRoomView,
    LeaveRoomView,
    UpdateRoom,
)

urlpatterns = [
    path("room", RoomView.as_view()),
    path("create-room", CreateRoomView.as_view()),
    path("get-room", GetRoomView.as_view()),
    path("join-room", JoinRoomView.as_view()),
    path("user-in-room", UserInRoomView.as_view()),
    path("leave-room", LeaveRoomView.as_view()),
    path("update-room", UpdateRoom.as_view()),
]
