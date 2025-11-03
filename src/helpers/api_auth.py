from ninja_jwt.authentication import JWTAuth


def allow_anon(request):
    if not request.user.is_authenticated:
        return True


api_auth_user_required = [JWTAuth()]
api_auth_user_or_anon = [JWTAuth(), allow_anon]
