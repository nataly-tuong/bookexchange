from .models import MainMenu

def menu_links(request):
    return {
        'item_list': MainMenu.objects.all()
    }