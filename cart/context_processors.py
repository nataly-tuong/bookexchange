from .cart_session import SessionCart
from .models import Cart


def cart_count(request):
    if request.user.is_authenticated:
        try:
            count = Cart.objects.get(user=request.user).get_total_items()
        except Cart.DoesNotExist:
            count = 0
    else:
        count = len(SessionCart(request))

    return {'cart_item_count': count}
