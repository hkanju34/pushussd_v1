
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

# Override default token views to handle token expiration
class CustomTokenObtainPairView(TokenObtainPairView):
    pass

class CustomTokenRefreshView(TokenRefreshView):
    pass