from django.http import (
    Http404,
    HttpRequest,
    HttpResponse,
    HttpResponseRedirect,
)
from django.shortcuts import (
    get_object_or_404,
    redirect,
    render,
)
from django.urls import reverse_lazy
from django.views.decorators.http import (
    require_GET,
    require_http_methods,
    require_POST,
)
from django.views.generic.edit import CreateView

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm

from django.db.models import Q

from .models import (
    Book,
    Comment,
    MainMenu,
    MessageThread,
    PrivateMessage,
)
from .forms import BookForm, CommentForm
# Create your views here.

'''
def index(request):
    return HttpResponse("<h1 align='center'>Hello World</h1> \
                        <h2>This is a try</h2> \
                        This is a test \
                        ")
'''

'''
def index(request):
    return render(request, 'base.html')
'''

def index(request):
    return render(request,
                  'bookMng/index.html',
                  {
                      'item_list': MainMenu.objects.all()
                  })

def postbook(request):
    submitted = False
    if request.method == 'POST':
        form = BookForm(request.POST, request.FILES)
        if form.is_valid():
            #form.save()
            book = form.save(commit=False)
            try:
                book.username = request.user
            except Exception:
                pass
            book.save()
            return HttpResponseRedirect('/postbook?submitted=True')
    else:
        form = BookForm()
        if 'submitted' in request.GET:
            submitted = True
    return render(request,
                  'bookMng/postbook.html',
                  {
                      'form': form,
                      'item_list': MainMenu.objects.all(),
                      'submitted': submitted
                  })

def displaybooks(request):
    books = Book.objects.all()
    for b in books:
        b.pic_path = b.picture.url[14:]

    return render(request,
                  'bookMng/displaybooks.html',
                  {
                      'item_list': MainMenu.objects.all(),
                      'books': books
                  })

def book_detail(request, book_id):
    book = Book.objects.get(id=book_id)


    book.pic_path = book.picture.url[14:]
    # comment addition
    comments = Comment.objects.filter(book=book)
    form = CommentForm()

    return render(request,
                  'bookMng/book_detail.html',
                  {
                      'item_list': MainMenu.objects.all(),
                      'book': book,
                      'comments': comments,
                      'form': form
                  })

def aboutus(request):
    return render(request,
                  'bookMng/aboutus.html',
                  {
                      'item_list': MainMenu.objects.all(),
                  })


def mybooks(request):
    books = Book.objects.filter(username=request.user)
    for b in books:
        b.pic_path = b.picture.url[14:]
    return render(request,
                  'bookMng/mybooks.html',
                  {
                      'item_list': MainMenu.objects.all(),
                      'books': books
                  })

def book_delete(request, book_id):
    book = Book.objects.get(id=book_id)
    book.delete()

    return render(request,
                  'bookMng/book_delete.html',
                  {
                      'item_list': MainMenu.objects.all(),
                  })

def searchbooks(request):
    query = request.GET.get('q', '')
    filter = request.GET.get('filter', 'any')

    if query:
        if filter == 'title':
            books = Book.objects.filter(name__icontains=query)
        if filter == 'user':
            books = Book.objects.filter(username__username__icontains=query)
        else:
            books = Book.objects.filter(Q(name__icontains=query) | Q(username__username__icontains=query)
)

    else:
        books = Book.objects.all()

    return render(request,
                  'bookMng/searchbooks.html',
                  {
                      'item_list': MainMenu.objects.all(),
                      'books': books,
                  })


def postcomment(request, book_id):
    book = get_object_or_404(Book, id=book_id)

    if request.method == 'POST':
        text = request.POST.get("text")
        comment_id = request.POST.get("comment_id")

        # Edit comment
        if comment_id:
            comment = get_object_or_404(Comment, id=comment_id)
            if request.user == comment.username:
                comment.text = text
                comment.save()

        # Create comment
        else:
            Comment.objects.create(
                book=book,
                username=request.user,
                text=text
            )

    return redirect('book_detail', book_id=book.id)

from .models import MessageThread, PrivateMessage

User = get_user_model()


@login_required
@require_GET
def inbox(request: HttpRequest) -> HttpResponse:
    threads = (
        MessageThread.objects
        .filter(Q(user1=request.user) | Q(user2=request.user))
        .prefetch_related("messages", "user1", "user2")
        .order_by("-updated_at")
    )

    thread_data = []
    for thread in threads:
        other_user = thread.other_user(request.user)
        latest_message = thread.latest_message()
        unread_count = thread.unread_count_for(request.user)
        thread_data.append(
            {
                "thread": thread,
                "other_user": other_user,
                "latest_message": latest_message,
                "unread_count": unread_count,
            }
        )

    context = {
        "thread_data": thread_data,
        'item_list': MainMenu.objects.all(),
    }
    return render(request, "bookMng/inbox.html", context)


@login_required
@require_http_methods(["GET", "POST"])
def thread_detail(request: HttpRequest, thread_id: int) -> HttpResponse:
    thread = get_object_or_404(
        MessageThread.objects.select_related("user1", "user2"),
        pk=thread_id,
    )

    if not thread.has_participant(request.user):
        raise Http404("Message thread not found.")

    if request.method == "POST":
        body = request.POST.get("body", "").strip()
        if not body:
            messages.error(request, "Message body cannot be empty.")
            return redirect("thread_detail", thread_id=thread.id)

        recipient = thread.other_user(request.user)
        PrivateMessage.objects.create(
            thread=thread,
            sender=request.user,
            recipient=recipient,
            body=body,
        )
        thread.save(update_fields=["updated_at"])
        messages.success(request, "Message sent.")
        return redirect("thread_detail", thread_id=thread.id)

    thread_messages = thread.messages.select_related("sender", "recipient").all()

    unread_messages = thread_messages.filter(recipient=request.user, is_read=False)
    for msg in unread_messages:
        msg.mark_as_read()

    context = {
        "thread": thread,
        "other_user": thread.other_user(request.user),
        "thread_messages": thread_messages,
        'item_list': MainMenu.objects.all(),
    }
    return render(request, "bookMng/thread.html", context)


@login_required
@require_http_methods(["GET", "POST"])
def compose_message(request: HttpRequest) -> HttpResponse:
    user_id = request.GET.get("user_id") or request.POST.get("user_id")
    selected_user = None

    if user_id:
        selected_user = get_object_or_404(User, pk=user_id)
        if selected_user == request.user:
            messages.error(request, "You cannot send a message to yourself.")
            return redirect("inbox")

    available_users = User.objects.exclude(pk=request.user.pk).order_by("username")

    if request.method == "POST":
        body = request.POST.get("body", "").strip()
        target_user_id = request.POST.get("user_id")

        if not target_user_id:
            messages.error(request, "Please choose a recipient.")
            return render(
                request,
                "bookMng/compose.html",
                {
                    "available_users": available_users,
                    "selected_user": selected_user,
                },
            )

        recipient = get_object_or_404(User, pk=target_user_id)

        if recipient == request.user:
            messages.error(request, "You cannot send a message to yourself.")
            return redirect("compose_message")

        if not body:
            messages.error(request, "Message body cannot be empty.")
            return render(
                request,
                "bookMng/compose.html",
                {
                    "available_users": available_users,
                    "selected_user": recipient,
                },
            )

        thread = MessageThread.get_or_create_thread(request.user, recipient)
        PrivateMessage.objects.create(
            thread=thread,
            sender=request.user,
            recipient=recipient,
            body=body,
        )
        thread.save(update_fields=["updated_at"])

        messages.success(request, f"Message sent to {recipient.username}.")
        return redirect("thread_detail", thread_id=thread.id)

    context = {
        "available_users": available_users,
        "selected_user": selected_user,
        'item_list': MainMenu.objects.all(),
    }
    return render(request, "bookMng/compose.html", context)


@login_required
@require_POST
def mark_thread_read(request: HttpRequest, thread_id: int) -> HttpResponse:
    thread = get_object_or_404(MessageThread, pk=thread_id)

    if not thread.has_participant(request.user):
        raise Http404("Message thread not found.")

    unread_messages = thread.messages.filter(recipient=request.user, is_read=False)
    for msg in unread_messages:
        msg.mark_as_read()

    messages.success(request, "Thread marked as read.")
    return redirect("thread_detail", thread_id=thread.id)

def comment_delete(request, comment_id):
    comment = Comment.objects.get(id=comment_id)
    book = comment.book

    if request.user == comment.username:
        comment.delete()

    return redirect('book_detail', book_id=book.id)


class Register(CreateView):
    template_name = 'registration/register.html'
    form_class = UserCreationForm
    success_url = reverse_lazy('register-success')

    def form_valid(self, form):
        form.save()
        return HttpResponseRedirect(self.success_url)