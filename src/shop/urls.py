from django.contrib.auth import views as auth_views
from django.urls import path, reverse_lazy

from . import views
from .forms import EmailLoginForm

app_name = "shop"

urlpatterns = [
    path("cart/", views.cart_detail, name="cart"),
    path("cart/add/<int:offer_id>/", views.cart_add, name="cart_add"),
    path("waitlist/<int:offer_id>/", views.waitlist_join, name="waitlist"),
    path("cart/update/", views.cart_update, name="cart_update"),
    path("cart/remove/<int:offer_id>/", views.cart_remove, name="cart_remove"),
    path("checkout/", views.checkout, name="checkout"),
    path("order/lookup/", views.order_lookup, name="order_lookup"),
    path("order/<str:token>/", views.order_detail, name="order"),
    path("order/<str:token>/download/<int:item_id>/", views.download, name="download"),
    # accounts (optional: guests can always check out without one)
    path("account/", views.account, name="account"),
    path("account/register/", views.register, name="register"),
    path(
        "account/login/",
        auth_views.LoginView.as_view(
            template_name="shop/login.html",
            authentication_form=EmailLoginForm,
            redirect_authenticated_user=True,
        ),
        name="login",
    ),
    path("account/logout/", auth_views.LogoutView.as_view(), name="logout"),
    path(
        "account/password-reset/",
        auth_views.PasswordResetView.as_view(
            template_name="shop/password_reset.html",
            email_template_name="shop/emails/password_reset.txt",
            subject_template_name="shop/emails/password_reset_subject.txt",
            success_url=reverse_lazy("shop:password_reset_done"),
        ),
        name="password_reset",
    ),
    path(
        "account/password-reset/sent/",
        auth_views.PasswordResetDoneView.as_view(
            template_name="shop/password_reset_done.html"
        ),
        name="password_reset_done",
    ),
    path(
        "account/reset/<uidb64>/<token>/",
        auth_views.PasswordResetConfirmView.as_view(
            template_name="shop/password_reset_confirm.html",
            success_url=reverse_lazy("shop:password_reset_complete"),
        ),
        name="password_reset_confirm",
    ),
    path(
        "account/reset/done/",
        auth_views.PasswordResetCompleteView.as_view(
            template_name="shop/password_reset_complete.html"
        ),
        name="password_reset_complete",
    ),
]
