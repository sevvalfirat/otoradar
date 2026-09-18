from django.urls import path
from . import views

urlpatterns = [
    path("", views.ListingListView.as_view(), name="listing-list"),
    path("<int:pk>/", views.ListingDetailView.as_view(), name="listing-detail"),
    path("new/", views.ListingCreateView.as_view(), name="listing-create"),
    path("<int:pk>/edit/", views.ListingUpdateView.as_view(), name="listing-update"),
    path("<int:pk>/delete/", views.ListingDeleteView.as_view(), name="listing-delete"),
    path("asistan/", views.AgentChatView.as_view(), name="agent-chat"),
]