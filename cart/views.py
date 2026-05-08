from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from bookMng.models import Book
from .cart_session import MAX_CART_QUANTITY, SessionCart, clean_quantity
from .models import Cart, CartItem
from django.contrib.auth.decorators import login_required



def _get_db_cart(user):
    cart, created = Cart.objects.get_or_create(user=user)
    return cart


def _get_db_cart_items(user):
    cart = _get_db_cart(user)
    items = cart.items.select_related('book', 'book__username')
    total = cart.get_total()
    total_items = cart.get_total_items()
    return items, total, total_items


def _enrich_db_items(db_items):
    return [
        {
            'book': item.book,
            'quantity': item.quantity,
            'price': item.book.price,
            'subtotal': item.get_subtotal(),
        }
        for item in db_items
    ]


def _set_pic_paths(items):
    for item in items:
        book = item['book']
        if book.picture:
            url = book.picture.url
            book.pic_path = url[14:] if url.startswith('/static/') else url.lstrip('/')


def cart_detail(request):
    if request.user.is_authenticated:
        db_items, total, total_items = _get_db_cart_items(request.user)
        items = _enrich_db_items(db_items)
    else:
        session_cart = SessionCart(request)
        items = session_cart.items_with_books()
        total = session_cart.get_total()
        total_items = len(session_cart)

    _set_pic_paths(items)

    return render(request, 'cart/cart_detail.html', {
        'items': items,
        'total': total,
        'total_items': total_items,
    })


@login_required
@require_POST
def cart_add(request, book_id):
    book = get_object_or_404(Book, pk=book_id)
    quantity = clean_quantity(request.POST.get('quantity', 1))

    if quantity <= 0:
        messages.warning(request, 'Please choose a valid quantity.')
        return redirect(request.POST.get('next') or 'cart:cart_detail')

    if request.user.is_authenticated:
        cart = _get_db_cart(request.user)
        item, created = CartItem.objects.get_or_create(cart=cart, book=book)

        if created:
            item.quantity = quantity
        else:
            item.quantity = min(item.quantity + quantity, MAX_CART_QUANTITY)

        item.save()
    else:
        SessionCart(request).add(book, quantity)

    messages.success(request, f'"{book.name}" added to your cart.')
    return redirect(request.POST.get('next') or 'cart:cart_detail')

@login_required
@require_POST
def cart_remove(request, book_id):
    book = get_object_or_404(Book, pk=book_id)

    if request.user.is_authenticated:
        try:
            cart = Cart.objects.get(user=request.user)
            CartItem.objects.filter(cart=cart, book=book).delete()
        except Cart.DoesNotExist:
            pass
    else:
        SessionCart(request).remove(book)

    messages.info(request, f'"{book.name}" removed from your cart.')
    return redirect('cart:cart_detail')

@login_required
@require_POST
def cart_update(request, book_id):
    book = get_object_or_404(Book, pk=book_id)
    quantity = clean_quantity(request.POST.get('quantity', 1))

    if request.user.is_authenticated:
        try:
            cart = Cart.objects.get(user=request.user)

            if quantity <= 0:
                CartItem.objects.filter(cart=cart, book=book).delete()
            else:
                item = CartItem.objects.get(cart=cart, book=book)
                item.quantity = quantity
                item.save()

        except (Cart.DoesNotExist, CartItem.DoesNotExist):
            pass
    else:
        SessionCart(request).update(book, quantity)

    return redirect('cart:cart_detail')

@login_required
def checkout(request):
    if request.user.is_authenticated:
        db_items, total, total_items = _get_db_cart_items(request.user)
        items = _enrich_db_items(db_items)
    else:
        session_cart = SessionCart(request)
        items = session_cart.items_with_books()
        total = session_cart.get_total()
        total_items = len(session_cart)

    if not items:
        messages.warning(request, 'Your cart is empty.')
        return redirect('cart:cart_detail')

    _set_pic_paths(items)

    if request.method == 'POST':
        if request.user.is_authenticated:
            try:
                Cart.objects.get(user=request.user).items.all().delete()
            except Cart.DoesNotExist:
                pass
        else:
            SessionCart(request).clear()

        messages.success(request, 'Order placed successfully! Thank you for your purchase.')
        return redirect('index')

    return render(request, 'cart/checkout.html', {
        'items': items,
        'total': total,
        'total_items': total_items,
    })
