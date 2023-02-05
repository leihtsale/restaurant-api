from rest_framework import serializers
from rest_framework.validators import UniqueTogetherValidator
from rest_framework import status
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.db.models import Sum
from .models import (
    Category,
    MenuItem,
    Cart,
    Order,
    OrderItem,
)


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = get_user_model()
        fields = ['id', 'username', 'password', 'first_name', 'last_name']
        extra_kwargs = {
            'password': {'write_only': True},
            'first_name': {'required': True},
            'last_name': {'required': True},
        }

    def create(self, validated_data):
        user = get_user_model().objects.create_user(**validated_data)
        customer_group = Group.objects.get(name='customer')
        user.groups.add(customer_group)
        return user


class CategorySerializer(serializers.ModelSerializer):

    class Meta:
        model = Category
        fields = '__all__'


class MenuItemSerializer(serializers.ModelSerializer):

    class Meta:
        model = MenuItem
        fields = ['id', 'title', 'price', 'featured', 'category']


class CartSerializer(serializers.ModelSerializer):
    user = serializers.HiddenField(
        default=serializers.CurrentUserDefault()
    )

    class Meta:
        model = Cart
        fields = '__all__'
        read_only_fields = ['unit_price', 'price']
        validators = [
            UniqueTogetherValidator(
                queryset=Cart.objects.all(),
                fields=['user', 'menuitem'],
                message="Item is already in the cart."
            )
        ]

    def validate(self, attrs):
        if attrs['quantity'] <= 0:
            raise serializers.ValidationError(
                'quantity cannot be 0 or less than 0.'
            )
        return attrs

    def create(self, validated_data):
        menuitem = validated_data.get('menuitem')
        unit_price = menuitem.price
        quantity = validated_data.get('quantity')
        price = unit_price * quantity
        validated_data['unit_price'] = unit_price
        validated_data['price'] = price
        return super().create(validated_data)


class OrderSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField()

    class Meta:
        model = Order
        fields = ['id', 'user', 'delivery_crew', 'status', 'total', 'date']
        read_only_fields = ['user', 'total', 'date']

    def validate(self, attrs):
        user = self.context['request'].user
        if user.groups.filter(name='delivery_crew').exists():
            if len(attrs) > 1 or ('status' not in attrs):
                raise serializers.ValidationError({
                    'detail': 'Only status field is editable.',
                })
        return attrs

    def create(self, validated_data):
        user = self.context['request'].user

        if not Cart.objects.filter(user=user).exists():
            raise serializers.ValidationError({
                'detail': 'Cart is empty.',
            }, code=status.HTTP_400_BAD_REQUEST)

        carts = Cart.objects.filter(user=user)
        order_total = carts.aggregate(Sum('price')).get('price__sum')
        order_data = {
            'user': user,
            'total': order_total,
        }
        order = Order.objects.create(**order_data)

        order_items = []
        for cart in carts:
            order_item = OrderItem(
                order=order,
                menuitem=cart.menuitem,
                quantity=cart.quantity,
                unit_price=cart.unit_price,
                price=cart.price
            )
            order_items.append(order_item)

        OrderItem.objects.bulk_create(order_items)
        carts.delete()

        return order


class OrderItemSerializer(serializers.ModelSerializer):

    class Meta:
        model = OrderItem
        fields = '__all__'
