from django.urls import path

from apps.accounts.auth_views import (
    CookieTokenLoginView,
    CookieTokenLogoutView,
    CookieTokenRefreshView,
    CsrfTokenView,
    VerifyEmailView,
)
from apps.accounts.views import RegisterView, UserProfileView

urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path("csrf/", CsrfTokenView.as_view(), name="csrf"),
    path("login/", CookieTokenLoginView.as_view(), name="login"),
    path("token/refresh/", CookieTokenRefreshView.as_view(), name="token_refresh"),
    path("logout/", CookieTokenLogoutView.as_view(), name="logout"),
    path("profile/", UserProfileView.as_view(), name="profile"),
    path("verify-email/", VerifyEmailView.as_view(), name="verify-email"),
]
