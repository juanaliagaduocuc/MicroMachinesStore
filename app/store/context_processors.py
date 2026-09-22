from .views import get_user_role


def user_role(request):
    return {
        'role': get_user_role(request.user),
        'user_name': request.user.first_name or request.user.username if request.user.is_authenticated else 'visitante',
    }
