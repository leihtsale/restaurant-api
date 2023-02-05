from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle, UserRateThrottle
from rest_framework.exceptions import NotFound
from rest_framework import (
    authentication,
    permissions,
    viewsets,
    generics,
    mixins,
    status,
)

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group

from . import permissions as custom_perms
from .models import (
    Category,
    MenuItem,
    Cart,
    Order,
)
from .serializers import (
    UserSerializer,
    CategorySerializer,
    MenuItemSerializer,
    CartSerializer,
    OrderSerializer,
    OrderItemSerializer,
)


class CreateUserView(generics.CreateAPIView):
    """
    Usage:
        - View for creating Users
    Permissions:
        - All. Authenticated or Unauthenticated requests are allowed.
    """
    serializer_class = UserSerializer
    permission_classes = [permissions.AllowAny]
    throttle_classes = [AnonRateThrottle]


class RetrieveUserView(generics.RetrieveAPIView):
    """
    Usage:
        - View for retrieving current user
    Permissions:
        - Requests/User must be authenticated.
    """
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.TokenAuthentication]
    throttle_classes = [UserRateThrottle]

    def get_object(self):
        return self.request.user


class ListCategories(generics.ListAPIView):
    """
    View for showing the list of categories
    """
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [permissions.IsAuthenticated]


class MenuItemViewSet(viewsets.ModelViewSet):
    """
    Usage:
        - View for creating, updating, listing, and deleting menu items.
    Permissions:
        - GET requests must be authenticated. All groups are allowed.
        - "customer" and "delivery_crew" groups, are not allowed
           to create, update, and delete a menu item.
        - Only "manager" group is allowed to create, update, and
          delete a menu item.
    """
    queryset = MenuItem.objects.all()
    serializer_class = MenuItemSerializer
    permission_classes = [
        permissions.IsAuthenticated,
        custom_perms.IsManager,
    ]
    authentication_classes = [authentication.TokenAuthentication]
    throttle_classes = [UserRateThrottle]

    filterset_fields = ['category', 'featured']
    ordering_fields = ['price']
    search_fields = ['title', 'category__title']

    def get_permissions(self):
        if self.request.method == "GET":
            self.permission_classes = [permissions.IsAuthenticated]
        return super().get_permissions()


class GroupView(mixins.ListModelMixin, generics.GenericAPIView):
    """
    Usage:
        - View for adding, listing, and removing member/s to a group.
    Permissions:
        - Only the "manager" group can see the list of managers
          and deliver crews, and remove a user from either of the group.
    """
    serializer_class = UserSerializer
    permission_classes = [
        permissions.IsAuthenticated,
        custom_perms.IsManager,
    ]
    authentication_classes = [authentication.TokenAuthentication]

    def initial(self, request, *args, **kwargs):
        role = kwargs.get('role')

        if role == 'manager':
            self.role = 'manager'
            self.queryset = get_user_model().objects.filter(
                groups__name='manager'
            )

        elif role == 'delivery-crew':
            self.role = 'delivery_crew'
            self.queryset = get_user_model().objects.filter(
                groups__name='delivery_crew'
            )

        else:
            raise NotFound()

        return super().initial(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        username = request.data.get('username')

        try:
            user = get_user_model().objects.get(username=username)

        except get_user_model().DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        belonged_group = Group.objects.get(name=self.role)
        user.groups.set([belonged_group])

        return Response(status=status.HTTP_201_CREATED)

    def delete(self, request, *args, **kwargs):
        user = self.get_object()
        customer_group = Group.objects.get(name='customer')
        user.groups.set([customer_group])

        return Response(status=status.HTTP_200_OK)


class ListCreateDeleteCartView(
        mixins.CreateModelMixin,
        mixins.ListModelMixin,
        generics.GenericAPIView):
    """
    Usage:
        - View for listing, creating, and deleting a cart.
    Permissions:
        - Only for the "customer" group.
    """
    serializer_class = CartSerializer
    permission_classes = [
        permissions.IsAuthenticated,
        custom_perms.IsCustomer,
    ]
    authentication_classes = [authentication.TokenAuthentication]

    def get_queryset(self):
        self.queryset = Cart.objects.filter(user=self.request.user)
        return super().get_queryset()

    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        return self.create(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):

        if not self.get_queryset().exists():
            return Response({
                'detail': 'Cart is already empty.'
            }, status=status.HTTP_400_BAD_REQUEST)

        self.get_queryset().delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class DeleteSingleItemCart(generics.DestroyAPIView):
    """
    Usage:
        - View for deleting a single item in a cart.
    Permissions:
        - Only customers are allowed to delete an item.
    """
    permission_classes = [
        permissions.IsAuthenticated,
        custom_perms.IsCustomer,
    ]
    authentication_classes = [authentication.TokenAuthentication]

    def get_queryset(self):
        self.queryset = Cart.objects.filter(user=self.request.user)
        return super().get_queryset()


class OrderViewSet(viewsets.ModelViewSet):
    """
    Usage:
        - View for listing, creating, updating, and deleting orders.
    Permissions:
        - customer:
            - GET, fetch a list of all belonged orders.
            - GET, retrieve a single order.
            - POST, place the current cart as an order.
        - manager:
            - GET, fetch a list of all orders.
            - PUT/PATCH, update an order
            - DELETE, delete an order
        - delivery_crew:
            - GET, fetch all orders with order items assigned.
            - PATCH, update the order status to 0 or 1
    """
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]
    authentication_classes = [authentication.TokenAuthentication]
    throttle_classes = [UserRateThrottle]

    filterset_fields = ['status']
    ordering_fields = ['date', 'total']
    search_fields = ['delivery_crew__username', 'user__username']
    throttle_classes = [UserRateThrottle]

    def get_permissions(self):
        method = self.request.method

        if (method == 'GET' and self.action == 'retrieve') or method == 'POST':
            self.permission_classes = [
                permissions.IsAuthenticated,
                custom_perms.IsCustomer,
            ]

        elif method == 'PUT' or method == 'DELETE':
            self.permission_classes = [
                permissions.IsAuthenticated,
                custom_perms.IsManager,
            ]

        elif method == 'PATCH':
            self.permission_classes = [
                permissions.IsAuthenticated,
                custom_perms.IsManager | custom_perms.IsDeliveryCrew,
            ]

        return super().get_permissions()

    def get_queryset(self):
        user = self.request.user
        group = user.groups.all()

        if group.filter(name='manager').exists():
            self.queryset = Order.objects.all()

        elif group.filter(name='customer').exists():
            self.queryset = Order.objects.filter(user=user)

        elif group.filter(name='delivery_crew').exists():
            self.queryset = Order.objects.filter(delivery_crew=user)

        return super().get_queryset()

    def retrieve(self, request, *args, **kwargs):
        user = request.user
        order = self.get_object()

        if user != order.user:
            return Response(status=status.HTTP_400_BAD_REQUEST)

        order_items = order.orderitem_set.all()
        serialized = OrderItemSerializer(order_items, many=True)

        return Response(serialized.data, status=status.HTTP_200_OK)
