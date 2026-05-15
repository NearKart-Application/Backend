from django.urls import path

from .views import (
    GroupCreateListView,
    GroupDetailView,
    GroupAddMemberView,
    GroupRemoveMemberView,
    GroupLeaveView,
    GroupProductListView,
    GroupFinalizeProductView,
)

urlpatterns = [
    path('',                                                       GroupCreateListView.as_view(),    name='group-create-list'),
    path('<uuid:group_id>/',                                       GroupDetailView.as_view(),        name='group-detail'),
    path('<uuid:group_id>/members/add/',                           GroupAddMemberView.as_view(),     name='group-add-member'),
    path('<uuid:group_id>/members/<uuid:user_id>/remove/',         GroupRemoveMemberView.as_view(),  name='group-remove-member'),
    path('<uuid:group_id>/leave/',                                 GroupLeaveView.as_view(),         name='group-leave'),
    path('<uuid:group_id>/products/',                              GroupProductListView.as_view(),   name='group-products'),
    path('<uuid:group_id>/products/<uuid:sp_id>/finalize/',        GroupFinalizeProductView.as_view(), name='group-finalize-product'),
]
