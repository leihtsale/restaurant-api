from rest_framework.authtoken.views import obtain_auth_token
from rest_framework.routers import SimpleRouter
from django.urls import path, include
from . import views


router = SimpleRouter(trailing_slash=False)
router.register('menu-items', views.MenuItemViewSet)
router.register('orders', views.OrderViewSet, basename='Order')

urlpatterns = [
    path('', include(router.urls)),
    path('users', views.CreateUserView.as_view()),
    path('users/me', views.RetrieveUserView.as_view()),
    path('token/login', obtain_auth_token),
    path('categories', views.ListCategories.as_view()),
    path('groups/<str:role>/users', views.GroupView.as_view()),
    path('groups/<str:role>/users/<int:pk>', views.GroupView.as_view()),
    path('cart/menu-items', views.ListCreateDeleteCartView.as_view()),
    path('cart/menu-items/<int:pk>', views.DeleteSingleItemCart.as_view())
]
