from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from listings.api_views import ListingViewSet

router = DefaultRouter()
router.register("listings", ListingViewSet)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include(router.urls)),   # ← agent bunu kullanacak
    path("", include("listings.urls")),
]