from rest_framework.permissions import BasePermission


class IsManager(BasePermission):

    message = "Only managers are allowed to do this action."

    def has_permission(self, request, view):
        return request.user.groups.filter(name='manager').exists()


class IsCustomer(BasePermission):

    message = "Only customers are allowed to do this action."

    def has_permission(self, request, view):
        return request.user.groups.filter(name='customer').exists()


class IsDeliveryCrew(BasePermission):

    message = "Only delivery crews are allowed to do this action."

    def has_permission(self, request, view):
        return request.user.groups.filter(name='delivery_crew').exists()
