from decimal import Decimal

CART_SESSION_KEY = 'cart'
MAX_CART_QUANTITY = 99


def clean_quantity(value, default=1):
    try:
        quantity = int(value)
    except (TypeError, ValueError):
        quantity = default
    return max(0, min(quantity, MAX_CART_QUANTITY))


class SessionCart:
    def __init__(self, request):
        self.session = request.session
        cart = self.session.get(CART_SESSION_KEY)

        if cart is None:
            cart = {}
            self.session[CART_SESSION_KEY] = cart

        self.cart = cart

    def _save(self):
        self.session.modified = True

    def _book_key(self, book):
        return str(book.pk)

    def add(self, book, quantity=1):
        quantity = clean_quantity(quantity)

        if quantity <= 0:
            return

        key = self._book_key(book)

        if key in self.cart:
            current_quantity = clean_quantity(self.cart[key].get('quantity', 0), default=0)
            self.cart[key]['quantity'] = min(current_quantity + quantity, MAX_CART_QUANTITY)
        else:
            self.cart[key] = {
                'quantity': quantity,
                'price': str(book.price),
                'name': book.name,
            }

        self._save()

    def remove(self, book):
        key = self._book_key(book)

        if key in self.cart:
            del self.cart[key]
            self._save()

    def update(self, book, quantity):
        quantity = clean_quantity(quantity)
        key = self._book_key(book)

        if quantity <= 0:
            self.remove(book)
        elif key in self.cart:
            self.cart[key]['quantity'] = quantity
            self._save()

    def clear(self):
        self.session[CART_SESSION_KEY] = {}
        self.session.modified = True
        self.cart = self.session[CART_SESSION_KEY]

    def __len__(self):
        return sum(clean_quantity(item.get('quantity', 0), default=0) for item in self.cart.values())

    def get_total(self):
        total = Decimal('0.00')

        for item in self.cart.values():
            quantity = clean_quantity(item.get('quantity', 0), default=0)
            price = Decimal(str(item.get('price', '0')))
            total += price * quantity

        return total

    def items_with_books(self):
        from bookMng.models import Book

        book_ids = []

        for key in self.cart.keys():
            try:
                book_ids.append(int(key))
            except ValueError:
                continue

        books = {book.pk: book for book in Book.objects.filter(pk__in=book_ids)}
        result = []

        for book_id, data in list(self.cart.items()):
            try:
                book = books.get(int(book_id))
            except ValueError:
                book = None

            if not book:
                del self.cart[book_id]
                self._save()
                continue

            quantity = clean_quantity(data.get('quantity', 1))

            if quantity <= 0:
                del self.cart[book_id]
                self._save()
                continue

            result.append({
                'book': book,
                'quantity': quantity,
                'price': book.price,
                'subtotal': book.price * quantity,
            })

        return result


def merge_session_cart_to_db(request):
    from .models import Cart, CartItem
    from bookMng.models import Book

    if not request.user.is_authenticated:
        return

    session_data = request.session.get(CART_SESSION_KEY, {})

    if not session_data:
        return

    cart, created = Cart.objects.get_or_create(user=request.user)

    for book_id, data in session_data.items():
        try:
            book = Book.objects.get(pk=int(book_id))
        except (Book.DoesNotExist, ValueError):
            continue

        quantity = clean_quantity(data.get('quantity', 1))

        if quantity <= 0:
            continue

        item, created = CartItem.objects.get_or_create(cart=cart, book=book)

        if created:
            item.quantity = quantity
        else:
            item.quantity = min(item.quantity + quantity, MAX_CART_QUANTITY)

        item.save()

    request.session[CART_SESSION_KEY] = {}
    request.session.modified = True
